"""
Enhanced News Collector with advanced features
Integrates Streamlit functionality with backend API
"""

import os
import re
import json
import time
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import asyncio

import requests
import feedparser
from bs4 import BeautifulSoup

# Import database
from database import db

# Setup logging
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

# HTTP Session with caching
HEADERS = {"User-Agent": "Mozilla/5.0 (NewsAgent/2.0; +https://github.com/newsbot)"}

try:
    if ENABLE_HTTP_CACHE:
        from requests_cache import CachedSession
        SESSION = CachedSession('http_cache', expire_after=HTTP_CACHE_EXPIRE)
    else:
        SESSION = requests.Session()
except ImportError:
    SESSION = requests.Session()
    logger.warning("requests-cache not available, using regular session")

# Configure HTTP adapter with retry strategy
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[429, 500, 502, 503, 504],
)
ADAPTER = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=retry_strategy
)
SESSION.mount("http://", ADAPTER)
SESSION.mount("https://", ADAPTER)

# Enhanced keyword processing
STOP_WORDS = {
    "기자", "뉴스", "특파원", "오늘", "매우", "기사", "사진", "영상", "제공", "입력",
    "것", "수", "등", "및", "그리고", "그러나", "하지만", "지난", "이번", "관련", "대한", "통해", "대해", "위해",
    "입니다", "한다", "했다", "하였다", "에서는", "에서", "대한", "이날", "라며", "다고", "였다", "했다가", "하며",
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our"
}

TECH_KEYWORDS = {
    # AI/ML
    "ai", "인공지능", "machine learning", "머신러닝", "deep learning", "딥러닝",
    "chatgpt", "gpt", "llm", "생성형ai", "generative ai", "신경망", "neural network",
    
    # Hardware/Semiconductors
    "반도체", "semiconductor", "메모리", "memory", "dram", "nand", "hbm",
    "gpu", "cpu", "npu", "tpu", "fpga", "asic", "칩셋", "chipset",
    "삼성전자", "samsung", "sk하이닉스", "tsmc", "엔비디아", "nvidia",
    
    # Communication/Network
    "5g", "6g", "lte", "와이파이", "wifi", "블루투스", "bluetooth",
    "클라우드", "cloud", "데이터센터", "data center", "서버", "server",
    "네트워크", "network", "cdn", "api", "sdk",
    
    # Blockchain/Fintech
    "블록체인", "blockchain", "암호화폐", "cryptocurrency", "bitcoin", "비트코인",
    "ethereum", "이더리움", "nft", "defi", "메타버스", "metaverse",
    
    # Automotive/Energy
    "자율주행", "autonomous", "전기차", "electric vehicle", "ev", "tesla", "테슬라",
    "배터리", "battery", "리튬", "lithium", "수소", "hydrogen",
    
    # Security
    "보안", "security", "해킹", "hacking", "사이버", "cyber", "랜섬웨어", "ransomware",
    "개인정보", "privacy", "데이터보호", "gdpr", "제로트러스트", "zero trust",
    
    # Software/Development
    "오픈소스", "open source", "개발자", "developer", "프로그래밍", "programming",
    "python", "javascript", "react", "node.js", "docker", "kubernetes",
}

class EnhancedNewsCollector:
    def __init__(self):
        self.session = SESSION
        self.stats = {
            'total_processed': 0,
            'total_inserted': 0,
            'total_updated': 0,
            'total_skipped': 0,
            'failed_feeds': [],
            'successful_feeds': []
        }
    
    def canonicalize_link(self, url: str) -> str:
        """Normalize and clean URL"""
        try:
            u = urlparse(url)
            scheme = (u.scheme or "https").lower()
            netloc = (u.netloc or "").lower()
            path = (u.path or "").rstrip("/")
            
            # Remove tracking parameters
            drop_params = {
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
                "gclid", "fbclid", "igshid", "spm", "ref", "ref_src", "cmpid", "source"
            }
            qs = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) 
                  if k.lower() not in drop_params]
            query = urlencode(qs, doseq=True)
            
            return urlunparse((scheme, netloc, path, u.params, query, ""))
        except Exception as e:
            logger.warning(f"URL canonicalization failed for {url}: {e}")
            return url
    
    def extract_main_text(self, url: str) -> str:
        """Extract main content from article URL"""
        try:
            response = self.session.get(
                url, 
                headers=HEADERS, 
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "aside", "advertisement"]):
                element.decompose()
            
            # Try to find main content
            content_selectors = [
                "article",
                "[id*='content']", "[class*='content']",
                "[id*='article']", "[class*='article']", 
                "[class*='post-content']", "[class*='entry-content']",
                "[id*='story']", "[class*='story']",
                "main", ".main-content"
            ]
            
            best_content = ""
            max_length = 0
            
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator="\n", strip=True)
                    if len(text) > max_length and len(text) > 200:
                        max_length = len(text)
                        best_content = text
            
            # Fallback to meta description
            if not best_content or len(best_content) < 100:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if not meta_desc:
                    meta_desc = soup.find("meta", attrs={"property": "og:description"})
                if meta_desc and meta_desc.get("content"):
                    best_content = meta_desc["content"]
            
            return best_content[:3000]  # Limit length
            
        except Exception as e:
            logger.warning(f"Failed to extract text from {url}: {e}")
            return ""
    
    def extract_keywords(self, text: str, title: str = "", top_k: int = 15) -> List[str]:
        """Enhanced keyword extraction"""
        if not text and not title:
            return []
        
        combined_text = f"{title} {text}".lower()
        keywords = []
        
        # 1. Extract tech keywords
        for keyword in TECH_KEYWORDS:
            if keyword in combined_text:
                keywords.append(keyword.title() if keyword.islower() else keyword)
        
        # 2. Extract patterns
        patterns = [
            r'\b[A-Z]{2,5}\b',  # Acronyms
            r'\b\d+[A-Za-z]{1,3}\b',  # Version numbers
            r'[가-힣]{2,8}(?:기술|시스템|플랫폼|서비스|솔루션)',  # Korean tech terms
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text + " " + title)
            for match in matches:
                if len(match) >= 2 and match.lower() not in STOP_WORDS:
                    keywords.append(match)
        
        # 3. Remove duplicates and filter
        unique_keywords = []
        seen = set()
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and kw_lower not in STOP_WORDS and len(kw) >= 2:
                unique_keywords.append(kw)
                seen.add(kw_lower)
        
        return unique_keywords[:top_k]
    
    def summarize_text(self, title: str, text: str, source: str) -> str:
        """Generate summary (with optional OpenAI integration)"""
        if ENABLE_SUMMARY and OPENAI_API_KEY:
            return self._openai_summarize(title, text, source)
        else:
            return self._heuristic_summarize(title, text)
    
    def _openai_summarize(self, title: str, text: str, source: str) -> str:
        """OpenAI-based summarization"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            prompt = f"""
다음 기사를 3-4문장으로 한국어 요약하세요. 사실 위주로 간결하게.
- 제목: {title}
- 출처: {source}
- 본문: {text[:2000]}

핵심 기술/제품/수치/일정을 포함하여 요약하세요.
"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 IT/기술 뉴스 전문 에디터입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            return summary if len(summary) > 20 else self._heuristic_summarize(title, text)
            
        except Exception as e:
            logger.warning(f"OpenAI summarization failed: {e}")
            return self._heuristic_summarize(title, text)
    
    def _heuristic_summarize(self, title: str, text: str) -> str:
        """Rule-based summarization"""
        if not text:
            return title
        
        # Clean and split into sentences
        clean_text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        
        # Take first 2-3 sentences
        summary_sentences = []
        char_count = 0
        for sentence in sentences:
            if char_count + len(sentence) > 300:
                break
            summary_sentences.append(sentence.strip())
            char_count += len(sentence)
            if len(summary_sentences) >= 3:
                break
        
        summary = " ".join(summary_sentences)
        return summary if summary else title
    
    def is_tech_article(self, title: str, text: str, keywords: List[str]) -> bool:
        """Determine if article is tech-related"""
        if not STRICT_TECH_KEYWORDS:
            return True
        
        combined = f"{title} {text} {' '.join(keywords)}".lower()
        
        # Check for tech keywords
        tech_score = sum(1 for kw in TECH_KEYWORDS if kw in combined)
        
        # Check for non-tech indicators
        non_tech_patterns = [
            "연예", "스포츠", "예능", "드라마", "영화", "음악", "게임",
            "요리", "여행", "패션", "뷰티", "건강", "운동", "다이어트"
        ]
        non_tech_score = sum(1 for pattern in non_tech_patterns if pattern in combined)
        
        return tech_score > non_tech_score and tech_score > 0
    
    def parse_feed(self, feed_url: str) -> Optional[object]:
        """Parse RSS feed with error handling"""
        try:
            feed = feedparser.parse(feed_url)
            if hasattr(feed, "entries") and feed.entries:
                return feed
            return None
        except Exception as e:
            logger.error(f"RSS parsing failed for {feed_url}: {e}")
            return None
    
    def expand_paged_feed_urls(self, feed_url: str, pages: int = RSS_BACKFILL_PAGES) -> List[str]:
        """Expand WordPress-style feeds with pagination"""
        urls = [feed_url]
        if re.search(r"/feed/?$", feed_url, re.IGNORECASE):
            for i in range(2, pages + 1):
                sep = "&" if "?" in feed_url else "?"
                urls.append(f"{feed_url}{sep}paged={i}")
        return urls
    
    # backend/enhanced_news_collector.py

def process_entry(entry_data: Dict, source: str, session: requests.Session) -> Optional[Dict]:
    """개별 뉴스 항목을 처리하고 데이터베이스에 저장할 형식으로 변환합니다 (오류 처리 강화)"""
    try:
        link = entry_data.get('link')
        if not link:
            return None

        # 이미 처리된 링크인지 확인 (메모리 기반 체크)
        # if is_recently_processed(link):
        #     return None

        title = entry_data.get('title', 'No Title')
        published_str = entry_data.get('published', datetime.now().isoformat())
        published_dt = parse_published_date(published_str)

        # User-Agent 추가하여 차단 방지
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        summary = None
        # 타임아웃을 30초로 늘려서 접속 시도
        try:
            response = session.get(link, timeout=30, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 메타 디스크립션 또는 본문에서 요약 추출
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                summary = meta_desc.get('content')
            else:
                article_body = soup.find('article') or soup.find('div', class_='article-body')
                if article_body:
                    summary = article_body.get_text(separator=' ', strip=True)[:300] + "..."
                else: # Fallback
                    summary = entry_data.get('summary', '')

        except requests.exceptions.RequestException as e:
            # 타임아웃을 포함한 모든 네트워크 오류를 여기서 처리하고 넘어감
            logger.warning(f"Could not fetch article content from {link}: {e}")
            summary = entry_data.get('summary', '') # RSS의 기본 요약 사용

        # 데이터베이스에 저장할 최종 기사 데이터
        article_data = {
            "title": title,
            "link": link,
            "published": published_dt.isoformat(),
            "source": source,
            "summary": summary,
            "keywords": None, 
        }
        return article_data

    except Exception as e:
        # 예상치 못한 다른 모든 오류를 처리하고 넘어감
        logger.error(f"An unexpected error occurred while processing entry {entry_data.get('link')}: {e}")
        return None
    
    def collect_from_feed(self, feed_config: Dict) -> List[Dict]:
        """Collect articles from single feed"""
        feed_url = feed_config.get("feed_url")
        source = feed_config.get("source", "Unknown")
        category = feed_config.get("category", "News")
        language = feed_config.get("lang", "en")
        
        if not feed_url:
            return []
        
        try:
            logger.info(f"📡 Collecting from {source}")
            
            # Expand URLs for pagination
            urls = self.expand_paged_feed_urls(feed_url)
            all_entries = []
            
            for url in urls[:3]:  # Limit pages
                feed = self.parse_feed(url)
                if feed and feed.entries:
                    entries = feed.entries[:MAX_RESULTS]
                    all_entries.extend(entries)
                    logger.info(f"  📄 {len(entries)} entries from page")
                
                if len(all_entries) >= MAX_TOTAL_PER_SOURCE:
                    break
            
            if not all_entries:
                logger.warning(f"❌ No entries found for {source}")
                self.stats['failed_feeds'].append(source)
                return []
            
            # Process entries in parallel
            articles = []
            if PARALLEL_MAX_WORKERS > 1:
                with ThreadPoolExecutor(max_workers=min(PARALLEL_MAX_WORKERS, 4)) as executor:
                    futures = [
                        executor.submit(self.process_entry, entry, source, category, language)
                        for entry in all_entries
                    ]
                    
                    for future in as_completed(futures):
                        try:
                            article = future.result()
                            if article:
                                articles.append(article)
                        except Exception as e:
                            logger.error(f"Error in parallel processing: {e}")
            else:
                # Sequential processing
                for entry in all_entries:
                    article = self.process_entry(entry, source, category, language)
                    if article:
                        articles.append(article)
            
            logger.info(f"✅ {source}: {len(articles)} articles processed")
            self.stats['successful_feeds'].append(source)
            return articles
            
        except Exception as e:
            logger.error(f"❌ Failed to collect from {source}: {e}")
            self.stats['failed_feeds'].append(source)
            return []
    
    def save_articles(self, articles: List[Dict]) -> Dict[str, int]:
        """Save articles to database"""
        if not articles:
            return {'inserted': 0, 'updated': 0, 'skipped': 0}
        
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
        
        for article in articles:
            try:
                # Check if article exists
                existing = db.execute_query(
                    "SELECT id FROM articles WHERE link = %s" if db.db_type == "postgresql" else
                    "SELECT id FROM articles WHERE link = ?",
                    (article['link'],)
                )
                
                if existing:
                    # Update existing article
                    if db.db_type == "postgresql":
                        db.execute_update("""
                            UPDATE articles SET 
                                title = %s, summary = %s, keywords = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE link = %s
                        """, (
                            article['title'],
                            article['summary'],
                            json.dumps(article['keywords']),
                            article['link']
                        ))
                    else:
                        db.execute_update("""
                            UPDATE articles SET 
                                title = ?, summary = ?, keywords = ?, updated_at = datetime('now')
                            WHERE link = ?
                        """, (
                            article['title'],
                            article['summary'],
                            json.dumps(article['keywords']),
                            article['link']
                        ))
                    stats['updated'] += 1
                else:
                    # Insert new article
                    article_id = db.insert_article(article)
                    if article_id:
                        stats['inserted'] += 1
                    else:
                        stats['skipped'] += 1
                        
            except Exception as e:
                logger.error(f"Error saving article: {e}")
                stats['skipped'] += 1
        
        return stats
    
    def collect_all_news(self, max_feeds: Optional[int] = None) -> Dict:
        """Collect news from all feeds"""
        logger.info("🚀 Starting comprehensive news collection")
        
        # Reset stats
        self.stats = {
            'total_processed': 0,
            'total_inserted': 0,
            'total_updated': 0,
            'total_skipped': 0,
            'failed_feeds': [],
            'successful_feeds': []
        }
        
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
        
        # Remove duplicates based on link
        unique_articles = []
        seen_links = set()
        for article in all_articles:
            if article['link'] not in seen_links:
                unique_articles.append(article)
                seen_links.add(article['link'])
        
        logger.info(f"📊 Collected {len(unique_articles)} unique articles")
        
        # Save to database
        if unique_articles:
            save_stats = self.save_articles(unique_articles)
            # Update stats with proper keys
            self.stats['total_inserted'] = save_stats.get('inserted', 0)
            self.stats['total_updated'] = save_stats.get('updated', 0)
            self.stats['total_skipped'] = save_stats.get('skipped', 0)
            self.stats['total_processed'] = len(unique_articles)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ Collection completed in {duration:.2f} seconds")
        logger.info(f"📈 Stats: {self.stats}")
        
        return {
            'success': True,
            'duration': duration,
            'stats': self.stats,
            'total_feeds': len(feeds_to_process),
            'successful_feeds': len(self.stats['successful_feeds']),
            'failed_feeds': len(self.stats['failed_feeds'])
        }

# Global collector instance
collector = EnhancedNewsCollector()

def collect_news_sync(max_feeds: Optional[int] = None) -> Dict:
    """Synchronous news collection"""
    return collector.collect_all_news(max_feeds)

async def collect_news_async(max_feeds: Optional[int] = None) -> Dict:
    """Asynchronous news collection"""
    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, collect_news_sync, max_feeds)
