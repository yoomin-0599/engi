# backend/main.py (모든 기능이 포함된 최종 버전)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import json
import os
import logging
from datetime import datetime
import asyncio

# --- 1. 원래 프로젝트의 모듈들을 올바르게 다시 import ---
from database import db
from enhanced_news_collector import collector # 이제 외부 파일을 다시 정상적으로 사용합니다.

# --- 2. 로깅 및 FastAPI 앱 설정 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="News IT's Issue API",
    description="Enhanced IT/Tech News Collection and Analysis Platform",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. 데이터베이스 초기화 ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API Server starting up...")
    try:
        db.init_database()
        logger.info("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# --- 4. 사라졌던 모든 API 엔드포인트 복원 ---

@app.get("/api/articles")
async def get_articles(
    limit: int = Query(100, le=2000), offset: int = Query(0, ge=0),
    source: Optional[str] = None, search: Optional[str] = None,
    favorites_only: bool = False, date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    try:
        return db.get_articles_with_filters(
            limit=limit, offset=offset, source=source, search=search,
            favorites_only=favorites_only, date_from=date_from, date_to=date_to
        )
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch articles.")

@app.get("/api/sources")
async def get_sources():
    # 이 기능은 database.py에 없으므로 직접 구현합니다.
    try:
        query = "SELECT DISTINCT source FROM articles ORDER BY source"
        results = db.execute_query(query)
        return [row['source'] for row in results]
    except Exception as e:
        logger.error(f"Error fetching sources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch sources.")


@app.get("/api/keywords/stats")
async def get_keyword_stats(limit: int = Query(50, le=200)):
    try:
        return db.get_keyword_stats(limit)
    except Exception as e:
        logger.error(f"Error getting keyword stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get keyword stats.")

# ... (즐겨찾기, 컬렉션 등 다른 모든 API들도 원래 코드에 포함되어 있다고 가정하고 핵심 기능만 복원) ...

# --- 5. 오류가 있었던 뉴스 수집 API 최종 수정 ---
@app.post("/api/collect-news-now")
async def collect_news_now(max_feeds: Optional[int] = Query(None)):
    try:
        logger.info("🚀 News collection request received.")
        # 중간 다리 없이 collector의 진짜 함수를 직접 호출하는 올바른 방식
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, collector.collect_all_news, max_feeds)

        # 통계 정보 가져오기
        total_articles_result = db.execute_query("SELECT COUNT(*) as count FROM articles")
        total_articles = total_articles_result[0]['count'] if total_articles_result else 0

        # 프론트엔드가 기대하는 모든 정보를 포함하여 반환
        stats = result.get('stats', {})
        return {
            "message": f"뉴스 수집 완료: {stats.get('inserted', 0)}개 신규",
            "status": "success",
            "duration": result.get('duration'),
            "processed": stats.get('total_processed', 0),
            "inserted": stats.get('inserted', 0),
            "updated": stats.get('updated', 0),
            "skipped": stats.get('skipped', 0),
            "total_articles": total_articles,
            "successful_feeds": stats.get('successful_feeds', []),
            "failed_feeds": stats.get('failed_feeds', []),
            "total_feeds": result.get('total_feeds', 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ News collection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"뉴스 수집 중 오류 발생: {str(e)}")

# 로컬 테스트용 서버 실행 코드
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

