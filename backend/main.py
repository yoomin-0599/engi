# backend/main.py (백그라운드 작업으로 수정, 디버그 엔드포인트 추가)

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
import logging
import os # os 모듈 추가

# --- 1. 프로젝트 모듈 import ---
from database import db, DB_PATH # DB_PATH 추가
from enhanced_news_collector import collector

# --- 2. 로깅 및 FastAPI 앱 설정 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="News IT's Issue API (Debug v2.2.3)", # 디버깅을 위해 제목 변경
    description="Enhanced IT/Tech News Collection and Analysis Platform",
    version="2.2.3" # 버전 업데이트
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Pydantic 모델 정의 ---
class Article(BaseModel):
    id: int
    title: str
    link: str
    published: str
    source: str
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_favorite: bool
    main_category: Optional[str] = None
    sub_category: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class FavoriteRequest(BaseModel):
    article_id: int

# --- 4. 데이터베이스 초기화 ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API Server starting up...")
    try:
        db.init_database()
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# --- 5. API 엔드포인트 ---

@app.get("/api/articles", response_model=List[Article])
async def get_articles(
    limit: int = Query(100, le=1000), offset: int = Query(0, ge=0),
    source: Optional[str] = None, search: Optional[str] = None,
    favorites_only: bool = False, date_from: Optional[str] = None,
    date_to: Optional[str] = None, main_category: Optional[str] = None
):
    try:
        return db.get_articles_with_filters(
            limit=limit, offset=offset, source=source, search=search,
            favorites_only=favorites_only, date_from=date_from, date_to=date_to,
            main_category=main_category
        )
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch articles.")

@app.get("/api/sources", response_model=List[str])
async def get_sources():
    try:
        results = db.execute_query("SELECT DISTINCT source FROM articles ORDER BY source")
        return [row['source'] for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch sources.")

@app.get("/api/keywords/stats")
async def get_keyword_stats(limit: int = 50):
    try:
        return db.get_keyword_stats(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get keyword stats.")

@app.get("/api/keywords/network")
async def get_keyword_network(limit: int = 30):
    try:
        return db.get_keyword_network_data(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get keyword network.")

@app.get("/api/categories/stats")
async def get_category_stats():
    try:
        query = "SELECT main_category as category, COUNT(*) as count FROM articles WHERE main_category != '기타' GROUP BY main_category ORDER BY count DESC"
        return db.execute_query(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get category stats.")

@app.post("/api/favorites/add")
async def add_favorite(request: FavoriteRequest):
    try:
        db.add_favorite(request.article_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to add favorite.")

@app.delete("/api/favorites/{article_id}")
async def remove_favorite(article_id: int):
    try:
        db.remove_favorite(article_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to remove favorite.")

# --- 6. 뉴스 수집 API --- 

def run_news_collection(max_feeds: Optional[int] = None):
    # 백그라운드에서 실행될 실제 뉴스 수집 함수
    try:
        logger.info(f"BACKGROUND: Starting news collection (max_feeds={max_feeds})...")
        collector.collect_all_news(max_feeds)
        logger.info("BACKGROUND: News collection finished.")
    except Exception as e:
        logger.error(f"BACKGROUND: News collection failed: {e}", exc_info=True)

@app.post("/api/collect-news-now")
async def collect_news_now(background_tasks: BackgroundTasks, max_feeds: Optional[int] = Query(None)):
    # 뉴스 수집을 백그라운드 작업으로 시작시키는 API
    logger.info("🚀 News collection request received. Starting as a background task.")
    background_tasks.add_task(run_news_collection, max_feeds)
    return {"message": "뉴스 수집 작업이 백그라운드에서 시작되었습니다. 완료까지 몇 분 정도 소요될 수 있습니다."}

# --- 7. 디버깅 엔드포인트 추가 ---
@app.get("/api/debug-info")
async def debug_info():
    db_path = DB_PATH
    db_exists = os.path.exists(db_path)
    try:
        article_count = db.execute_query("SELECT COUNT(*) as count FROM articles")[0]['count']
    except Exception as e:
        article_count = f"Error: {e}"
    
    return {
        "db_path": db_path,
        "db_exists": db_exists,
        "article_count": article_count
    }

# 로컬 테스트용
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)