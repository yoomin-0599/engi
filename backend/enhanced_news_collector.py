# backend/enhanced_news_collector.py (모든 기능이 복원되고 안정화된 최종 버전)

import logging
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser
import requests
from bs4 import BeautifulSoup
import dateutil.parser

from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. 원래 프로젝트의 전체 RSS 피드 목록 복원 ---
FEEDS = [
    {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아", "category": "IT", "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.bloter.net/feed", "source": "Bloter", "category": "IT", "lang": "ko"},
    {"feed_url": "https://byline.network/feed/", "source": "Byline Network", "category": "IT", "lang": "ko"},
    {"feed_url": "https://platum.kr/feed", "source": "Platum", "category": "Startup", "lang": "ko"},
    {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch", "category": "Tech", "lang": "en"},
    {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "category": "Tech", "lang": "en"},
    {"feed_url": "https://www.wired.com/feed/rss", "source": "WIRED", "category": "Tech", "lang": "en"},
]

# --- 2. 원래 프로젝트의 고급 키워드 목록 복원 ---
STOP_WORDS = {"기자", "뉴스", "특파원", "오늘", "사진", "영상", "제공", "입력", "것", "수", "등", "및"}
TECH_KEYWORDS = {
    "ai", "인공지능", "머신러닝", "딥러닝", "chatgpt", "gpt", "llm", "생성형ai",
    "반도체", "semiconductor", "dram", "nand", "hbm", "gpu", "cpu", "npu",
    "삼성전자", "samsung", "sk하이닉스", "tsmc", "엔비디아", "nvidia",
    "5g", "6g", "클라우드", "cloud", "데이터센터", "서버", "server",
    "블록체인", "blockchain", "암호화폐", "metaverse", "메타버스",
    "자율주행", "전기차", "ev", "배터리", "battery",
    "보안", "security", "해킹", "hacking", "cyber", "랜섬웨어",
    "오픈소스", "open source", "개발자", "developer", "python", "react",
}

class EnhancedNewsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.stats = {}

    def _extract_keywords(self, text: str, title: str, top_k: int = 15) -> List[str]:
        """[복원된 기능] 규칙 기반으로 고급 키워드를 추출합니다."""
        if not text and not title: return []
        combined_text = f"{title} {text}".lower()
        keywords = {kw for kw in TECH_KEYWORDS if kw in combined_text}
        acronyms = re.findall(r'\b[A-Z]{3,}\b', f"{title} {text}")
        keywords.update(acronyms)
        
        unique_keywords = [kw for kw in list(keywords) if kw.lower() not in STOP_WORDS and len(kw) > 1]
        return unique_keywords[:top_k]

    def _extract_main_text(self, url: str) -> Optional[str]:
        """[복원된 기능] 기사 URL에 직접 접속하여 본문 텍스트를 추출합니다."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = self.session.get(url, timeout=20, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "aside"]): element.decompose()
            
            content_selectors = ["article", "[class*='article']", "[id*='content']", "main"]
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = element.get_text(separator="\n", strip=True)
                    if len(main_content) > 200: return main_content
            return None
        except Exception as e:
            logger.warning(f"본문 추출 실패: {url} - {e}")
            return None

    def _process_entry(self, entry: Dict, source: str, category: str, lang: str) -> Optional[Dict]:
        title = entry.get("title", "No Title").strip()
        link = entry.get("link", "").strip()
        if not title or not link: return None

        try: published = dateutil.parser.parse(entry.get("published", "")).isoformat()
        except: published = datetime.now().isoformat()

        summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(separator=' ', strip=True)
        main_text = self._extract_main_text(link)
        keywords = self._extract_keywords(main_text or summary, title)

        return {'title': title, 'link': link, 'published': published, 'source': source,
                'summary': summary, 'keywords': keywords, 'raw_text': main_text,
                'category': category, 'language': lang}

    def collect_from_feed(self, feed_config: Dict) -> List[Dict]:
        feed_url, source = feed_config.get("feed_url"), feed_config.get("source", "Unknown")
        logger.info(f"📡 {source}에서 뉴스 수집 시작...")
        try:
            response = self.session.get(feed_url, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if not feed or not feed.entries:
                logger.warning(f"❌ {source}에서 기사를 찾을 수 없습니다."); return []
            
            articles = [self._process_entry(entry, source, feed_config.get("category"), feed_config.get("lang")) for entry in feed.entries[:20]]
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

