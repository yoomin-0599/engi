# backend/enhanced_news_collector.py (정교한 키워드 사전이 반영된 최종 버전)

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

# Enhanced configuration
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "15"))
MAX_TOTAL_PER_SOURCE = int(os.getenv("MAX_TOTAL_PER_SOURCE", "200"))
RSS_BACKFILL_PAGES = int(os.getenv("RSS_BACKFILL_PAGES", "3"))

CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "10.0"))
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "15.0"))

ENABLE_SUMMARY = os.getenv("ENABLE_SUMMARY", "false").lower() == "true"
ENABLE_HTTP_CACHE = os.getenv("ENABLE_HTTP_CACHE", "true").lower() == "true"
HTTP_CACHE_EXPIRE = int(os.getenv("HTTP_CACHE_EXPIRE", "3600"))
PARALLEL_MAX_WORKERS = int(os.getenv("PARALLEL_MAX_WORKERS", "8"))
SKIP_UPDATE_IF_EXISTS = os.getenv("SKIP_UPDATE_IF_EXISTS", "true").lower() == "true"

STRICT_TECH_KEYWORDS = os.getenv("STRICT_TECH_KEYWORDS", "true").lower() == "true"
SKIP_NON_TECH = os.getenv("SKIP_NON_TECH", "false").lower() == "true"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- 1. 사용자 제공 카테고리 및 키워드 사전 ---
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

# --- 2. [추가] 사용자 제공 기술 키워드 및 불용어 사전 ---
STOP_WORDS = {
    "기자", "뉴스", "특파원", "오늘", "매우", "기사", "사진", "영상", "제공", "입력",
    "것", "수", "등", "및", "그리고", "그러나", "하지만", "지난", "이번", "관련", "대한", "통해", "대해", "위해",
    "입니다", "한다", "했다", "하였다", "에서는", "에서", "대한", "이날", "라며", "다고", "였다", "했다가", "하며",
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our"
}

TECH_KEYWORDS = {
    "ai", "인공지능", "machine learning", "머신러닝", "deep learning", "딥러닝",
    "chatgpt", "gpt", "llm", "생성형ai", "generative ai", "신경망", "neural network",
    "반도체", "semiconductor", "메모리", "memory", "dram", "nand", "hbm",
    "gpu", "cpu", "npu", "tpu", "fpga", "asic", "칩셋", "chipset",
    "삼성전자", "samsung", "sk하이닉스", "tsmc", "엔비디아", "nvidia",
    "5g", "6g", "lte", "와이파이", "wifi", "블루투스", "bluetooth",
    "클라우드", "cloud", "데이터센터", "data center", "서버", "server",
    "네트워크", "network", "cdn", "api", "sdk",
    "블록체인", "blockchain", "암호화폐", "cryptocurrency", "bitcoin", "비트코인",
    "ethereum", "이더리움", "nft", "defi", "메타버스", "metaverse",
    "자율주행", "autonomous", "전기차", "electric vehicle", "ev", "tesla", "테슬라",
    "배터리", "battery", "리튬", "lithium", "수소", "hydrogen",
    "보안", "security", "해킹", "hacking", "사이버", "cyber", "랜섬웨어", "ransomware",
    "개인정보", "privacy", "데이터보호", "gdpr", "제로트러스트", "zero trust",
    "오픈소스", "open source", "개발자", "developer", "프로그래밍", "programming",
    "python", "javascript", "react", "node.js", "docker", "kubernetes",
}

# Comprehensive RSS feeds (Korean + Global)
FEEDS = [
    # Korean Tech News
    {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아", "category": "IT", "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보", "category": "IT", "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section901.xml", "source": "전자신문_오늘의뉴스", "category": "IT", "lang": "ko"},
    {"feed_url": "https://zdnet.co.kr/news/news_xml.asp", "source": "ZDNet Korea", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.itworld.co.kr/rss/all.xml", "source": "ITWorld Korea", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.ciokorea.com/rss/all.xml", "source": "CIO Korea", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.bloter.net/feed", "source": "Bloter", "category": "IT", "lang": "ko"},
    {"feed_url": "https://byline.network/feed/", "source": "Byline Network", "category": "IT", "lang": "ko"},
    {"feed_url": "https://platum.kr/feed", "source": "Platum", "category": "Startup", "lang": "ko"},
    {"feed_url": "https://www.boannews.com/media/news_rss.xml", "source": "보안뉴스", "category": "Security", "lang": "ko"},
    {"feed_url": "https://it.chosun.com/rss.xml", "source": "IT조선", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.ddaily.co.kr/news_rss.php", "source": "디지털데일리", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.kbench.com/rss.xml", "source": "KBench", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.sedaily.com/rss/IT.xml", "source": "서울경제 IT", "category": "IT", "lang": "ko"},
    {"feed_url": "https://www.hankyung.com/feed/it", "source": "한국경제 IT", "category": "IT", "lang": "ko"},
    
    # Global Tech News
    {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch", "category": "Tech", "lang": "en"},
    {"feed_url": "https://www.eetimes.com/feed/", "source": "EE Times", "category": "Electronics", "lang": "en"},
    {"feed_url": "https://spectrum.ieee.org/rss/fulltext", "source": "IEEE Spectrum", "category": "Engineering", "lang": "en"},
    {"feed_url": "https://www.technologyreview.com/feed/", "source": "MIT Tech Review", "category": "Tech", "lang": "en"},
    {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "category": "Tech", "lang": "en"},
    {"feed_url": "https://www.wired.com/feed/rss", "source": "WIRED", "category": "Tech", "lang": "en"},
    {"feed_url": "https://www.engadget.com/rss.xml", "source": "Engadget", "category": "Tech", "lang": "en"},
    {"feed_url": "https://venturebeat.com/category/ai/feed/", "source": "VentureBeat AI", "category": "AI", "lang": "en"},
    {"feed_url": "https://arstechnica.com/feed/", "source": "Ars Technica", "category": "Tech", "lang": "en"},
    {"feed_url": "https://feeds.feedburner.com/oreilly/radar", "source": "O'Reilly Radar", "category": "Tech", "lang": "en"},
]

class EnhancedNewsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.stats = {}

    def _classify_article(self, text: str) -> Dict:
        """기사 텍스트를 기반으로 카테고리를 분류합니다."""
        best_match = {'score': 0, 'main': '기타', 'sub': '기타'}
        for main_cat, subcats in CATEGORIES.items():
            for sub_cat, keywords in subcats.items():
                score = sum(1 for kw in keywords if kw in text)
                if score > best_match['score']:
                    best_match = {'score': score, 'main': main_cat, 'sub': sub_cat}
        return {'main_category': best_match['main'], 'sub_category': best_match['sub']}

    def extract_main_text(self, url: str) -> str:
        """기사 URL에 직접 접속하여 본문 텍스트를 추출합니다."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = self.session.get(url, timeout=20, headers=headers, allow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "aside", "header"]): element.decompose()
            
            content_selectors = ["article", "[class*='article']", "[id*='content']", "main", "[class*='post-content']"]
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = element.get_text(separator="\n", strip=True)
                    if len(main_content) > 200: return main_content
            return ""
        except Exception as e:
            logger.warning(f"본문 추출 실패: {url} - {e}")
            return ""
    
    def extract_keywords(self, text: str, title: str, top_k: int = 15) -> List[str]:
        """정교한 방식으로 키워드를 추출합니다."""
        if not text and not title: return []
        combined_text = f"{title} {text}".lower()
        keywords = {kw for kw in TECH_KEYWORDS if kw in combined_text}
        
        patterns = [r'\b[A-Z]{3,}\b', r'[가-힣]{2,8}(?:기술|시스템|플랫폼)']
        for pattern in patterns:
            matches = re.findall(pattern, f"{title} {text}")
            keywords.update(matches)
        
        unique_keywords = [kw for kw in list(keywords) if kw.lower() not in STOP_WORDS and len(kw) > 1]
        return unique_keywords[:top_k]

    def process_entry(self, entry: Dict, source: str, language: str) -> Optional[Dict]:
        """개별 뉴스 항목을 처리하고, 분류 및 키워드 추출을 수행합니다."""
        title = entry.get("title", "No Title").strip()
        link = entry.get("link", "").strip()
        if not title or not link: return None

        try: published = dateutil.parser.parse(entry.get("published", "")).isoformat()
        except: published = datetime.now().isoformat()

        summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(separator=' ', strip=True)
        raw_text = self.extract_main_text(link)
        
        full_text = f"{title} {summary} {raw_text}"
        classification = self._classify_article(full_text)
        keywords = self.extract_keywords(raw_text or summary, title)

        return {
            'title': title, 'link': link, 'published': published, 'source': source,
            'summary': summary, 'keywords': keywords, 'raw_text': raw_text,
            'main_category': classification['main_category'],
            'sub_category': classification['sub_category'],
            'language': language
        }

    def collect_from_feed(self, feed_config: Dict) -> List[Dict]:
        feed_url, source, lang = feed_config.get("feed_url"), feed_config.get("source"), feed_config.get("lang")
        logger.info(f"📡 {source}에서 뉴스 수집 시작...")
        try:
            response = self.session.get(feed_url, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if not feed or not feed.entries:
                logger.warning(f"❌ {source}에서 기사를 찾을 수 없습니다."); return []
            
            articles = [self.process_entry(entry, source, lang) for entry in feed.entries[:20]]
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
        
        # Process feeds in parallel
        if PARALLEL_MAX_WORKERS > 1:
            with ThreadPoolExecutor(max_workers=min(PARALLEL_MAX_WORKERS, len(feeds_to_process))) as executor:
                future_to_feed = {
                    executor.submit(self.collect_from_feed, feed): feed 
                    for feed in feeds_to_process
                }
                
                for future in as_completed(future_to_feed):
                    try:
                        articles = future.result(timeout=60)  # 60 second timeout per feed
                        all_articles.extend(articles)
                    except Exception as e:
                        feed = future_to_feed[future]
                        logger.error(f"Feed collection failed: {feed.get('source', 'Unknown')}: {e}")
        else:
            # Sequential processing
            for feed in feeds_to_process:
                articles = self.collect_from_feed(feed)
                all_articles.extend(articles)
                
        unique_articles = list({article['link']: article for article in all_articles}.values())
        if unique_articles:
            save_stats = self.save_articles(unique_articles)
        else:
            save_stats = {}
        
        duration = time.time() - start_time
        return {'status': 'success', 'duration': duration, 'stats': save_stats}

collector = EnhancedNewsCollector()
