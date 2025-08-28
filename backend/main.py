# backend/main.py (최종 통합 버전)

import os
import re
import json
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import asyncio

import requests
import feedparser
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# --- 1. 모든 필요한 모듈을 파일 상단에 정리 ---
from database import db

# --- 2. 로깅 설정 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 3. EnhancedNewsCollector 클래스 정의 (외부 파일 대신 여기에 직접 포함) ---
class EnhancedNewsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.stats = {}

    def collect_from_feed(self, feed_config):
        feed_url = feed_config.get("feed_url")
        source = feed_config.get("source", "Unknown")
        logger.info(f"📡 Collecting from {source}")
        try:
            feed = feedparser.parse(feed_url)
            if not feed or not feed.entries:
                logger.warning(f"❌ No entries found for {source}")
                return []

            articles = []
            for entry in feed.entries[:15]: # Limit entries
                title = getattr(entry, "title", "No Title").strip()
                link = getattr(entry, "link", "").strip()
                if not title or not link:
                    continue

                published = getattr(entry, "published", datetime.now().isoformat())
                summary = getattr(entry, "summary", "")
                articles.append({'title': title, 'link': link, 'published': published, 'source': source, 'summary': summary, 'keywords': []})

            logger.info(f"✅ {source}: {len(articles)} articles processed")
            return articles
        except Exception as e:
            logger.error(f"❌ Failed to collect from {source}: {e}")
            return []

    def save_articles(self, articles):
        stats = {'inserted': 0, 'skipped': 0, 'updated': 0}
        for article in articles:
            try:
                if db.insert_article(article):
                    stats['inserted'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                logger.error(f"Error saving article {article.get('link')}: {e}")
                stats['skipped'] += 1
        return stats

    def collect_all_news(self, max_feeds: Optional[int] = None):
        logger.info("🚀 Starting comprehensive news collection")
        self.stats = {'total_processed': 0, 'total_inserted': 0, 'total_updated': 0, 'total_skipped': 0, 'failed_feeds': [], 'successful_feeds': []}
        start_time = time.time()

        # 소스 코드를 참고한 전체 FEEDS 리스트
        FEEDS = [
            {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
            {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보"},
            {"feed_url": "https://www.bloter.net/feed", "source": "Bloter"},
            {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
            {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
        ]
        feeds_to_process = FEEDS[:max_feeds] if max_feeds else FEEDS

        all_articles = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self.collect_from_feed, feed) for feed in feeds_to_process]
            for future in as_completed(futures):
                all_articles.extend(future.result())

        unique_articles = list({article['link']: article for article in all_articles}.values())
        logger.info(f"📊 Collected {len(unique_articles)} unique articles")

        if unique_articles:
            save_stats = self.save_articles(unique_articles)
            self.stats.update(save_stats)

        duration = time.time() - start_time
        return {'status': 'success', 'duration': duration, 'stats': self.stats}

# --- 4. FastAPI 앱 설정 ---
app = FastAPI(title="News IT's Issue API")
collector = EnhancedNewsCollector() # 통합된 클래스로 인스턴스 생성

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API Server starting up...")
    try:
        db.init_database()
        logger.info("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# --- 5. API 엔드포인트 정의 ---
@app.get("/api/articles")
async def get_articles(limit: int = 100, offset: int = 0):
    try:
        return db.get_articles_with_filters(limit=limit, offset=offset)
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch articles.")

@app.post("/api/collect-news-now")
async def collect_news_now(max_feeds: Optional[int] = Query(None)):
    try:
        logger.info("🚀 News collection request received.")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, collector.collect_all_news, max_feeds)

        total_articles_result = db.execute_query("SELECT COUNT(*) as count FROM articles")
        total_articles = total_articles_result[0]['count'] if total_articles_result else 0

        return {
            "message": "뉴스 수집 완료",
            "status": "success",
            "duration": result.get('duration'),
            "inserted": result.get('stats', {}).get('inserted', 0),
            "total_articles": total_articles
        }
    except Exception as e:
        logger.error(f"❌ News collection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"뉴스 수집 중 오류 발생: {str(e)}")

# --- 서버 실행 (로컬 테스트용) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)








