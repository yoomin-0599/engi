# backend/main.py

import asyncio
import logging
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

# --- 1. 프로젝트 모듈 import ---
# 이제 외부 파일을 정상적으로 다시 참조합니다.
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
    allow_origins=["*"],  # 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. 데이터베이스 초기화 ---
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 데이터베이스를 초기화합니다."""
    logger.info("🚀 API 서버가 시작됩니다...")
    try:
        db.init_database()
        logger.info("✅ 데이터베이스가 성공적으로 초기화되었습니다.")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")

# --- 4. Pydantic 데이터 모델 정의 ---
# 프론트엔드와 통신할 데이터의 형식을 엄격하게 정의합니다.

class Article(BaseModel):
    id: int
    title: str
    link: str
    published: str
    source: str
    summary: Optional[str] = None
    keywords: Optional[List[str]] = []
    is_favorite: bool

    model_config = ConfigDict(from_attributes=True)

class KeywordStat(BaseModel):
    keyword: str
    count: int

class NetworkNode(BaseModel):
    id: str
    label: str
    value: int

class NetworkEdge(BaseModel):
    source: str
    target: str
    value: int

class NetworkData(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]

class FavoriteRequest(BaseModel):
    article_id: int

# --- 5. API 엔드포인트 복원 및 개선 ---

@app.get("/api/articles", response_model=List[Article])
async def get_articles(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False
):
    """모든 뉴스 기사 목록을 필터링과 함께 조회합니다."""
    try:
        return db.get_articles_with_filters(
            limit=limit, offset=offset, source=source,
            search=search, favorites_only=favorites_only
        )
    except Exception as e:
        logger.error(f"기사 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="기사 조회 중 오류가 발생했습니다.")

@app.get("/api/sources", response_model=List[str])
async def get_sources():
    """수집된 모든 뉴스 출처 목록을 조회합니다."""
    try:
        return db.get_all_sources()
    except Exception as e:
        logger.error(f"뉴스 출처 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="뉴스 출처 조회 중 오류가 발생했습니다.")

@app.get("/api/keywords/stats", response_model=List[KeywordStat])
async def get_keyword_stats(limit: int = Query(50, le=200)):
    """가장 많이 등장한 키워드 통계를 조회합니다."""
    try:
        return db.get_keyword_stats(limit)
    except Exception as e:
        logger.error(f"키워드 통계 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="키워드 통계 조회 중 오류가 발생했습니다.")

@app.get("/api/keywords/network", response_model=NetworkData)
async def get_keyword_network(limit: int = Query(30, le=100)):
    """키워드 관계 네트워크 데이터를 조회합니다."""
    try:
        return db.get_keyword_network_data(limit)
    except Exception as e:
        logger.error(f"키워드 네트워크 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="키워드 네트워크 데이터 생성 중 오류가 발생했습니다.")

@app.post("/api/favorites/add")
async def add_favorite(request: FavoriteRequest):
    """특정 기사를 즐겨찾기에 추가합니다."""
    try:
        db.add_favorite(request.article_id)
        return {"status": "success", "message": "즐겨찾기에 추가되었습니다."}
    except Exception as e:
        logger.error(f"즐겨찾기 추가 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="즐겨찾기 추가 중 오류가 발생했습니다.")

@app.delete("/api/favorites/remove/{article_id}")
async def remove_favorite(article_id: int):
    """특정 기사를 즐겨찾기에서 제거합니다."""
    try:
        db.remove_favorite(article_id)
        return {"status": "success", "message": "즐겨찾기에서 제거되었습니다."}
    except Exception as e:
        logger.error(f"즐겨찾기 제거 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="즐겨찾기 제거 중 오류가 발생했습니다.")

@app.post("/api/collect-news-now")
async def collect_news_now(max_feeds: Optional[int] = Query(None)):
    """즉시 뉴스 수집을 시작하고 결과를 반환합니다."""
    try:
        logger.info("🚀 뉴스 수집 요청을 받았습니다.")
        loop = asyncio.get_event_loop()
        # 오래 걸리는 작업을 별도의 스레드에서 실행하여 서버 차단 방지
        result = await loop.run_in_executor(None, collector.collect_all_news, max_feeds)
        
        total_articles_result = db.execute_query("SELECT COUNT(*) as count FROM articles")
        total_articles = total_articles_result[0]['count'] if total_articles_result else 0
        
        stats = result.get('stats', {})
        return {
            "message": "뉴스 수집이 완료되었습니다.",
            "status": "success",
            "duration": result.get('duration'),
            "inserted": stats.get('inserted', 0),
            "total_articles": total_articles,
        }
    except Exception as e:
        logger.error(f"❌ 뉴스 수집 중 심각한 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"뉴스 수집 중 오류 발생: {str(e)}")

# 로컬 테스트용 서버 실행 코드
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
