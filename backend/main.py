# backend/main.py (모든 기능이 포함된 최종 버전)

import asyncio
import logging
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

# --- 1. 프로젝트 모듈 import ---
from database import db
from enhanced_news_collector import collector

# --- 2. 로깅 및 FastAPI 앱 설정 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="뉴스있슈~ API (News IT's Issue)",
    description="IT/공학 뉴스 수집, 분석, 시각화 플랫폼",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- 3. 데이터베이스 초기화 ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API 서버가 시작됩니다...")
    try:
        db.init_database()
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")

# --- 4. Pydantic 데이터 모델 정의 ---
class Article(BaseModel):
    id: int; title: str; link: str; published: str; source: str
    summary: Optional[str] = None; keywords: Optional[List[str]] = []
    is_favorite: bool
    model_config = ConfigDict(from_attributes=True)

class KeywordStat(BaseModel):
    keyword: str; count: int

class NetworkNode(BaseModel):
    id: str; label: str; value: int

class NetworkEdge(BaseModel):
    source: str; target: str; value: int

class NetworkData(BaseModel):
    nodes: List[NetworkNode]; edges: List[NetworkEdge]

class FavoriteRequest(BaseModel):
    article_id: int

# --- 5. API 엔드포인트 복원 및 개선 ---

@app.get("/api/articles", response_model=List[Article])
async def get_articles(
    limit: int = 100, offset: int = 0, source: Optional[str] = None,
    search: Optional[str] = None, favorites_only: bool = False
):
    try:
        return db.get_articles_with_filters(
            limit=limit, offset=offset, source=source,
            search=search, favorites_only=favorites_only
        )
    except Exception as e:
        logger.error(f"기사 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="기사 조회 중 오류 발생")

@app.get("/api/sources", response_model=List[str])
async def get_sources():
    try: return db.get_all_sources()
    except Exception as e:
        logger.error(f"소스 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="뉴스 출처 조회 중 오류 발생")

@app.get("/api/keywords/stats", response_model=List[KeywordStat])
async def get_keyword_stats(limit: int = 50):
    try: return db.get_keyword_stats(limit)
    except Exception as e:
        logger.error(f"키워드 통계 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="키워드 통계 조회 중 오류 발생")

@app.get("/api/keywords/network", response_model=NetworkData)
async def get_keyword_network(limit: int = 30):
    try: return db.get_keyword_network_data(limit)
    except Exception as e:
        logger.error(f"키워드 네트워크 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="네트워크 데이터 생성 중 오류 발생")

@app.post("/api/favorites/add")
async def add_favorite(request: FavoriteRequest):
    try:
        db.add_favorite(request.article_id)
        return {"status": "success", "message": "즐겨찾기에 추가되었습니다."}
    except Exception as e:
        logger.error(f"즐겨찾기 추가 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="즐겨찾기 추가 중 오류 발생")

@app.delete("/api/favorites/{article_id}")
async def remove_favorite(article_id: int):
    try:
        db.remove_favorite(article_id)
        return {"status": "success", "message": "즐겨찾기에서 제거되었습니다."}
    except Exception as e:
        logger.error(f"즐겨찾기 제거 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="즐겨찾기 제거 중 오류 발생")

@app.post("/api/collect-news-now")
async def collect_news_now(max_feeds: Optional[int] = Query(None)):
    try:
        logger.info("🚀 뉴스 수집 요청을 받았습니다.")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, collector.collect_all_news, max_feeds)
        
        total_articles = db.execute_query("SELECT COUNT(*) as count FROM articles")[0]['count']
        stats = result.get('stats', {})
        return {
            "message": "뉴스 수집 완료", "status": "success",
            "duration": result.get('duration'), "inserted": stats.get('inserted', 0),
            "total_articles": total_articles, "updated": stats.get('updated', 0)
        }
    except Exception as e:
        logger.error(f"❌ 뉴스 수집 중 심각한 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"뉴스 수집 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

