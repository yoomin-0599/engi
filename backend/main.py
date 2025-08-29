# backend/main.py (카테고리 기능이 추가된 최종 버전)



from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
import logging
from datetime import datetime
import asyncio
import translators as ts

# --- 1. 프로젝트 모듈 import ---
from database import db
from enhanced_news_collector import collector

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

# --- 3. Pydantic 모델 정의 (데이터 형식 검증) ---
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
    translated_title: Optional[str] = None
    translated_summary: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class FavoriteRequest(BaseModel):
    article_id: int

class Collection(BaseModel):
    id: int
    name: str

class Stats(BaseModel):
    total_articles: int
    total_sources: int
    total_favorites: int

# --- 4. 데이터베이스 초기화 ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API Server starting up...")
    try:
        db.init_database()
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# --- 5. 모든 API 엔드포인트 복원 ---

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
        db.execute_update("INSERT OR IGNORE INTO favorites (article_id) VALUES (?)", (request.article_id,))
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to add favorite.")

@app.delete("/api/favorites/{article_id}")
async def remove_favorite(article_id: int):
    try:
        db.execute_update("DELETE FROM favorites WHERE article_id = ?", (article_id,))
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to remove favorite.")

@app.get("/api/collections", response_model=List[Collection])
async def get_collections():
    try:
        return db.execute_query("SELECT id, name FROM collections ORDER BY name")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get collections.")
        
@app.get("/api/stats", response_model=Stats)
async def get_stats():
    try:
        total_articles = db.execute_query("SELECT COUNT(*) as count FROM articles")[0]['count']
        total_sources = db.execute_query("SELECT COUNT(DISTINCT source) as count FROM articles")[0]['count']
        total_favorites = db.execute_query("SELECT COUNT(*) as count FROM favorites")[0]['count']
        return {"total_articles": total_articles, "total_sources": total_sources, "total_favorites": total_favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get stats.")

# --- 6. 뉴스 수집 및 번역 API 최종 수정 ---
@app.post("/api/collect-news-now")
async def collect_news_now(max_feeds: Optional[int] = Query(None)):
    try:
        logger.info("🚀 News collection request received.")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, collector.collect_all_news, max_feeds)
        return result
    except Exception as e:
        logger.error(f"❌ News collection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"뉴스 수집 중 오류 발생: {str(e)}")

@app.post("/api/articles/{article_id}/translate")
async def translate_article(article_id: int):
    try:
        article = db.execute_query("SELECT title, summary, language FROM articles WHERE id = ?", (article_id,))
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        if article[0]['language'] != 'en':
            return {"message": "영문 기사만 번역할 수 있습니다."}

        text_to_translate = f"{article[0]['title']}. {article[0]['summary']}"
        translated_text = ts.translate_text(text_to_translate, translator='google', to_language='ko')
        
        parts = translated_text.split('. ', 1)
        translated_title = parts[0]
        translated_summary = parts[1] if len(parts) > 1 else ""

        db.execute_update(
            "UPDATE articles SET translated_title = ?, translated_summary = ? WHERE id = ?",
            (translated_title, translated_summary, article_id)
        )
        return {"translated_title": translated_title, "translated_summary": translated_summary}
    except Exception as e:
        logger.error(f"Translation error for article {article_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"번역 실패: {str(e)}")

# 로컬 테스트용
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
