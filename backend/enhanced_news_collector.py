# backend/enhanced_news_collector.py

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup
from kiwipiepy import Kiwi # 한국어 형태소 분석기

from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kiwi 형태소 분석기 초기화 (명사만 추출)
kiwi = Kiwi()
kiwi.prepare()

# 수집할 RSS 피드 목록
FEEDS = [
    {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
    {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보"},
    {"feed_url": "https://www.bloter.net/feed", "source": "Bloter"},
    {"feed_url": "https://byline.network/feed/", "source": "Byline Network"},
    {"feed_url": "https://platum.kr/feed", "source": "Platum"},
    {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
    {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
    {"feed_url": "https://www.wired.com/feed/rss", "source": "WIRED"},
]

class EnhancedNewsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.stats = {}

    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Kiwi를 사용하여 텍스트에서 명사 키워드를 추출합니다."""
        if not text:
            return []
        
        # 형태소 분석 실행 (NNG: 일반 명사, NNP: 고유 명사)
        result = kiwi.analyze(text[:1000], top_n=top_n, pos_score=0.8)
        
        keywords = []
        if result and result[0]:
            for token, pos, _, _ in result[0][0]:
                if pos in ('NNG', 'NNP') and len(token) > 1:
                    keywords.append(token)
        
        # 중복 제거 및 순서 유지
        return sorted(list(set(keywords)), key=keywords.index)


    def _process_entry(self, entry: Dict, source: str) -> Optional[Dict]:
        """개별 뉴스 항목을 처리하고 키워드를 추출합니다."""
        try:
            title = entry.get("title", "No Title").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                return None

            published_str = entry.get("published", datetime.now().isoformat())
            try:
                import dateutil.parser
                published = dateutil.parser.parse(published_str).isoformat()
            except:
                published = datetime.now().isoformat()

            # HTML 태그 제거 및 요약 정리
            summary_html = entry.get("summary", "")
            summary = BeautifulSoup(summary_html, "html.parser").get_text(separator=' ', strip=True)

            # 키워드 추출
            keywords = self._extract_keywords(f"{title} {summary}")

            return {
                'title': title, 'link': link, 'published': published,
                'source': source, 'summary': summary, 'keywords': keywords
            }
        except Exception as e:
            logger.error(f"항목 처리 중 오류 발생 ({entry.get('link')}): {e}")
            return None

    def collect_from_feed(self, feed_config: Dict) -> List[Dict]:
        """단일 RSS 피드에서 뉴스를 수집합니다."""
        feed_url = feed_config.get("feed_url")
        source = feed_config.get("source", "Unknown")
        logger.info(f"📡 {source}에서 뉴스 수집 시작...")
        try:
            # 타임아웃 설정으로 무한 대기 방지
            response = self.session.get(feed_url, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if not feed or not feed.entries:
                logger.warning(f"❌ {source}에서 기사를 찾을 수 없습니다.")
                return []
            
            articles = [self._process_entry(entry, source) for entry in feed.entries[:20]]
            valid_articles = [article for article in articles if article]
            
            logger.info(f"✅ {source}: {len(valid_articles)}개 기사 처리 완료.")
            return valid_articles
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {source} 수집 실패 (네트워크 오류): {e}")
            return []
        except Exception as e:
            logger.error(f"❌ {source} 수집 실패 (알 수 없는 오류): {e}")
            return []

    def save_articles(self, articles: List[Dict]) -> Dict:
        """수집된 기사들을 데이터베이스에 저장합니다."""
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
        for article in articles:
            try:
                # 데이터베이스에 기사를 삽입하거나 업데이트합니다.
                result = db.insert_or_update_article(article)
                stats[result] += 1
            except Exception as e:
                logger.error(f"DB 저장 오류 ({article.get('link')}): {e}")
                stats['skipped'] += 1
        return stats

    def collect_all_news(self, max_feeds: Optional[int] = None) -> Dict:
        """모든 RSS 피드에서 뉴스를 수집하고 저장합니다."""
        logger.info("🚀 전체 뉴스 수집 작업을 시작합니다.")
        self.stats = {'total_processed': 0, 'total_inserted': 0, 'total_updated': 0, 'total_skipped': 0}
        start_time = time.time()
        
        feeds_to_process = FEEDS[:max_feeds] if max_feeds else FEEDS
        
        all_articles = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_feed = {executor.submit(self.collect_from_feed, feed): feed for feed in feeds_to_process}
            for future in as_completed(future_to_feed):
                all_articles.extend(future.result())
        
        unique_articles = list({article['link']: article for article in all_articles}.values())
        logger.info(f"📊 총 {len(unique_articles)}개의 고유한 기사를 수집했습니다.")
        
        if unique_articles:
            save_stats = self.save_articles(unique_articles)
            self.stats.update(save_stats)
        
        duration = time.time() - start_time
        self.stats['total_processed'] = len(unique_articles)
        logger.info(f"✅ 전체 수집 완료. (소요 시간: {duration:.2f}초)")
        return {'status': 'success', 'duration': duration, 'stats': self.stats}

# 다른 파일에서 쉽게 사용할 수 있도록 인스턴스 생성
collector = EnhancedNewsCollector()
