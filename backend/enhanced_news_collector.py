# backend/enhanced_news_collector.py (카테고리 분류 기능이 추가된 최종 버전)

import logging
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup
import dateutil.parser

from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. 레퍼런스 코드를 참고한 카테고리 사전 정의 ---
CATEGORIES = {
    "첨단 제조·기술 산업": {
        "반도체": ["반도체", "메모리", "dram", "nand", "hbm", "파운드리", "foundry", "euv"],
        "자동차": ["자동차", "전기차", "ev", "수소차", "하이브리드", "자율주행", "adas", "모빌리티"],
        "이차전지": ["이차전지", "2차전지", "배터리", "ess", "전고체", "ncm", "lfp", "양극재", "음극재"],
        "디스플레이": ["디스플레이", "oled", "amoled", "lcd", "qd", "마이크로 led"],
        "로봇·스마트팩토리": ["로봇", "스마트팩토리", "산업용 로봇", "협동로봇", "cobot", "디지털트윈"],
    },
    "디지털·ICT 산업": {
        "AI": ["ai", "인공지능", "머신러닝", "딥러닝", "생성형 ai", "챗봇", "llm"],
        "ICT·통신": ["5g", "6g", "네트워크", "통신", "위성통신", "클라우드", "데이터센터", "엣지 컴퓨팅"],
        "소프트웨어·플랫폼": ["소프트웨어", "메타버스", "vr", "ar", "xr", "saas", "핀테크", "플랫폼", "ott", "게임", "보안", "빅데이터", "블록체인"],
    },
}

FEEDS = [
    {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
    {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보"},
    {"feed_url": "https://www.bloter.net/feed", "source": "Bloter"},
    {"feed_url": "https://byline.network/feed/", "source": "Byline Network"},
    {"feed_url": "https://platum.kr/feed", "source": "Platum"},
    {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
    {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
]

class EnhancedNewsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.stats = {}

    def _classify_article(self, title: str, content: str) -> Dict:
        """[추가된 기능] 기사 제목/본문으로 카테고리를 자동 분류합니다."""
        text = f"{title} {content}".lower()
        best_match = {'score': 0, 'main': '기타', 'sub': '기타'}

        for main_cat, subcats in CATEGORIES.items():
            for sub_cat, keywords in subcats.items():
                score = sum(1 for kw in keywords if kw in text)
                if score > best_match['score']:
                    best_match = {'score': score, 'main': main_cat, 'sub': sub_cat}
        
        return {'main_category': best_match['main'], 'sub_category': best_match['sub']}

    def _extract_keywords_simple(self, text: str, top_n: int = 10) -> List[str]:
        if not text: return []
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        candidates = [word for word in words if len(word) > 1 and not word.isnumeric()]
        stop_words = {"기자", "뉴스", "사진", "제공", "이번", "지난"}
        keywords = [word for word in candidates if word not in stop_words]
        return list(dict.fromkeys(keywords))[:top_n]

    def _process_entry(self, entry: Dict, source: str) -> Optional[Dict]:
        title = entry.get("title", "No Title").strip()
        link = entry.get("link", "").strip()
        if not title or not link: return None

        try: published = dateutil.parser.parse(entry.get("published", "")).isoformat()
        except: published = datetime.now().isoformat()

        summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(separator=' ', strip=True)
        keywords = self._extract_keywords_simple(f"{title} {summary}")
        
        # [추가] 카테고리 분류 실행
        classification = self._classify_article(title, summary)

        article_data = {
            'title': title, 'link': link, 'published': published,
            'source': source, 'summary': summary, 'keywords': keywords,
            'main_category': classification['main_category'],
            'sub_category': classification['sub_category'],
        }
        return article_data

    def collect_from_feed(self, feed_config: Dict) -> List[Dict]:
        feed_url, source = feed_config.get("feed_url"), feed_config.get("source", "Unknown")
        logger.info(f"📡 {source}에서 뉴스 수집 시작...")
        try:
            response = self.session.get(feed_url, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if not feed or not feed.entries:
                logger.warning(f"❌ {source}에서 기사를 찾을 수 없습니다."); return []
            
            articles = [self._process_entry(entry, source) for entry in feed.entries[:20]]
            valid_articles = [article for article in articles if article]
            logger.info(f"✅ {source}: {len(valid_articles)}개 기사 처리 완료.")
            return valid_articles
        except Exception as e:
            logger.error(f"❌ {source} 수집 실패: {e}"); return []

    def save_articles(self, articles: List[Dict]) -> Dict:
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
        for article in articles:
            try:
                result = db.insert_or_update_article(article); stats[result] += 1
            except Exception as e:
                logger.error(f"DB 저장 오류 ({article.get('link')}): {e}"); stats['skipped'] += 1
        return stats

    def collect_all_news(self, max_feeds: Optional[int] = None) -> Dict:
        logger.info("🚀 전체 뉴스 수집 작업을 시작합니다.")
        start_time = time.time()
        feeds_to_process = FEEDS[:max_feeds] if max_feeds else FEEDS
        
        all_articles = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_feed = {executor.submit(self.collect_from_feed, feed): feed for feed in feeds_to_process}
            for future in as_completed(future_to_feed):
                all_articles.extend(future.result())
        
        unique_articles = list({article['link']: article for article in all_articles}.values())
        if unique_articles:
            save_stats = self.save_articles(unique_articles)
        else:
            save_stats = {}
        
        duration = time.time() - start_time
        return {'status': 'success', 'duration': duration, 'stats': save_stats}

collector = EnhancedNewsCollector()

