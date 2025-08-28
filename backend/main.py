from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Set, Any
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import enhanced modules
try:
    from database import db, init_db, get_db_connection
    from enhanced_news_collector import collector, collect_news_async
    ENHANCED_MODULES_AVAILABLE = True
    logger.info("✅ Enhanced modules loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to load enhanced modules: {e}")
    ENHANCED_MODULES_AVAILABLE = False

# Fallback imports
if not ENHANCED_MODULES_AVAILABLE:
    logger.info("🔄 Using fallback modules")
    try:
        from simple_news_collector import collect_all_feeds, FEEDS
        SIMPLE_COLLECTOR_AVAILABLE = True
    except ImportError:
        SIMPLE_COLLECTOR_AVAILABLE = False
        logger.error("❌ No news collector available")

app = FastAPI(
    title="News IT's Issue API",
    description="Enhanced IT/Tech News Collection and Analysis Platform",
    version="2.0.0"
)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"

# CORS configuration
if ENABLE_CORS:
    origins = [
    "http://localhost:5173",  # 로컬 개발 환경
    "https://enginews.netlify.app",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 모든 주소 허용 (진단용)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Database initialization
_db_initialized = False

async def ensure_db_initialized():
    """Ensure database is initialized"""
    global _db_initialized
    if not _db_initialized:
        try:
            if ENHANCED_MODULES_AVAILABLE:
                db.init_database()
            else:
                # Fallback initialization
                import sqlite3
                conn = sqlite3.connect("/tmp/news.db")
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        link TEXT UNIQUE NOT NULL,
                        published TEXT,
                        source TEXT,
                        summary TEXT,
                        keywords TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.commit()
                conn.close()
            _db_initialized = True
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise HTTPException(status_code=500, detail="Database initialization failed")

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Starting News IT's Issue API Server")
    await ensure_db_initialized()
    
    # Log configuration
    logger.info(f"Database type: {db.db_type if ENHANCED_MODULES_AVAILABLE else 'SQLite'}")
    logger.info(f"Enhanced modules: {'Available' if ENHANCED_MODULES_AVAILABLE else 'Not Available'}")
    logger.info(f"OpenAI API: {'Configured' if OPENAI_API_KEY else 'Not Configured'}")
    logger.info(f"PostgreSQL: {'Available' if DATABASE_URL else 'Not Available'}")

class Article(BaseModel):
    id: int
    title: str
    link: str
    published: str
    source: str
    summary: Optional[str]
    keywords: Optional[str]
    created_at: Optional[str]
    is_favorite: bool = False

class FavoriteRequest(BaseModel):
    article_id: int

class KeywordStats(BaseModel):
    keyword: str
    count: int

class NetworkNode(BaseModel):
    id: str
    label: str
    value: int

class NetworkEdge(BaseModel):
    from_node: str = None
    to: str
    value: int

    model_config = {"field_alias_generator": None}
    
    def dict(self, **kwargs):
        data = super().model_dump(**kwargs)
        if 'from_node' in data:
            data['from'] = data.pop('from_node')
        return data

class CollectionRequest(BaseModel):
    name: str
    rules: Optional[Dict] = None

class NewsCollectionRequest(BaseModel):
    days: int = 30
    max_pages: int = 5

# get_db_connection is now imported from database module

@app.get("/api/articles")
async def get_articles(
    limit: int = Query(100, le=2000),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get articles with filtering and pagination"""
    await ensure_db_initialized()
    
    try:
        if ENHANCED_MODULES_AVAILABLE:
            articles = db.get_articles_with_filters(
                limit=limit,
                offset=offset,
                source=source,
                search=search,
                favorites_only=favorites_only,
                date_from=date_from,
                date_to=date_to
            )
            return articles
        else:
            # Fallback implementation
            import sqlite3
            conn = sqlite3.connect("/tmp/news.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT *, 0 as is_favorite FROM articles WHERE 1=1"
            params = []
            
            if source:
                query += " AND source = ?"
                params.append(source)
            
            if search:
                query += " AND (title LIKE ? OR summary LIKE ? OR keywords LIKE ?)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            query += " ORDER BY published DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            articles = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return articles
            
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources")
async def get_sources():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT source FROM articles ORDER BY source")
    sources = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sources

@app.get("/api/keywords/stats")
async def get_keyword_stats(limit: int = Query(50, le=200)):
    """Get keyword statistics"""
    await ensure_db_initialized()
    
    try:
        if ENHANCED_MODULES_AVAILABLE:
            return db.get_keyword_stats(limit)
        else:
            # Fallback implementation
            import sqlite3
            conn = sqlite3.connect("/tmp/news.db")
            cursor = conn.cursor()
            cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL")
            
            keyword_counter = {}
            for row in cursor.fetchall():
                try:
                    if row[0]:
                        # Try to parse as JSON, fallback to comma-split
                        try:
                            keywords = json.loads(row[0])
                        except:
                            keywords = row[0].split(',')
                        
                        for kw in keywords:
                            kw = kw.strip()
                            if kw:
                                keyword_counter[kw] = keyword_counter.get(kw, 0) + 1
                except Exception:
                    continue
            
            conn.close()
            
            sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"keyword": k, "count": v} for k, v in sorted_keywords]
            
    except Exception as e:
        logger.error(f"Error getting keyword stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/keywords/network")
async def get_keyword_network(limit: int = Query(30, le=100)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL")
    
    keyword_docs = []
    for row in cursor.fetchall():
        keywords = row[0].split(',') if row[0] else []
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        if keywords:
            keyword_docs.append(keywords)
    
    conn.close()
    
    keyword_counter = {}
    cooccurrence = {}
    
    for doc_keywords in keyword_docs:
        for kw in doc_keywords:
            keyword_counter[kw] = keyword_counter.get(kw, 0) + 1
        
        for i, kw1 in enumerate(doc_keywords):
            for kw2 in doc_keywords[i+1:]:
                pair = tuple(sorted([kw1, kw2]))
                cooccurrence[pair] = cooccurrence.get(pair, 0) + 1
    
    top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
    top_keyword_set = {k for k, _ in top_keywords}
    
    nodes = [{"id": kw, "label": kw, "value": count} for kw, count in top_keywords]
    edges = []
    
    for (kw1, kw2), weight in cooccurrence.items():
        if kw1 in top_keyword_set and kw2 in top_keyword_set and weight > 1:
            edges.append({"from": kw1, "to": kw2, "value": weight})
    
    return {"nodes": nodes, "edges": edges}

@app.get("/api/favorites")
async def get_favorites():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.* FROM articles a
        JOIN favorites f ON a.id = f.article_id
        ORDER BY f.created_at DESC
    """)
    
    favorites = []
    for row in cursor.fetchall():
        article = dict(row)
        article['is_favorite'] = True
        favorites.append(article)
    
    conn.close()
    return favorites

@app.post("/api/favorites/add")
async def add_favorite(request: FavoriteRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO favorites (article_id) VALUES (?)",
            (request.article_id,)
        )
        conn.commit()
        return {"success": True, "message": "Favorite added"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/favorites/{article_id}")
async def remove_favorite(article_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Favorite removed"}

@app.get("/api/stats")
async def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT source) FROM articles")
    total_sources = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM favorites")
    total_favorites = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT DATE(published) as date, COUNT(*) as count 
        FROM articles 
        WHERE published >= date('now', '-7 days')
        GROUP BY DATE(published)
        ORDER BY date
    """)
    daily_counts = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_articles": total_articles,
        "total_sources": total_sources,
        "total_favorites": total_favorites,
        "daily_counts": daily_counts
    }

# Inline news collection functions
def collect_from_rss(feed_url: str, source: str, max_items: int = 10):
    """Collect articles from RSS feed"""
    try:
        import feedparser
        import requests
        from datetime import datetime
        
        print(f"📡 Collecting from {source}...")
        
        feed = feedparser.parse(feed_url)
        if not hasattr(feed, 'entries') or not feed.entries:
            return []
        
        articles = []
        for entry in feed.entries[:max_items]:
            try:
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                
                if not title or not link:
                    continue
                
                published = getattr(entry, 'published', datetime.now().strftime('%Y-%m-%d'))
                summary = getattr(entry, 'summary', '')[:500] if hasattr(entry, 'summary') else ''
                
                articles.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'source': source,
                    'summary': summary
                })
                
            except Exception:
                continue
        
        print(f"✅ Collected {len(articles)} from {source}")
        return articles
        
    except Exception as e:
        print(f"❌ Error collecting from {source}: {e}")
        return []

def save_articles_to_db(articles):
    """Save articles to database"""
    if not articles:
        return {'inserted': 0, 'skipped': 0}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {'inserted': 0, 'skipped': 0}
    
    for article in articles:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO articles (title, link, published, source, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (
                article['title'],
                article['link'],
                article['published'],
                article['source'],
                article['summary']
            ))
            
            if cursor.rowcount > 0:
                stats['inserted'] += 1
            else:
                stats['skipped'] += 1
                
        except Exception:
            stats['skipped'] += 1
    
    conn.commit()
    conn.close()
    return stats

def run_collection():
    """Run news collection from major sources"""
    
    # Try simple collector first (no pandas dependency)
    if USE_SIMPLE_COLLECTOR:
        try:
            print("Using simple news collector...")
            # Ensure DB is initialized
            ensure_db_initialized()
            
            # Import and use simple collector with current DB
            import simple_news_collector
            simple_news_collector.DB_PATH = DB_PATH  # Use the same DB path
            
            # Collect news from all feeds
            all_articles = []
            for feed in SIMPLE_FEEDS[:10]:  # Limit to first 10 feeds for quick collection
                articles = collect_from_feed(feed['feed_url'], feed['source'], max_items=5)
                all_articles.extend(articles)
            
            if all_articles:
                # Save to our database
                stats = save_articles_to_db(all_articles)
                return True, len(all_articles), stats
                
        except Exception as e:
            print(f"Error using simple collector: {e}")
    
    # Try full news_collector as second option
    if USE_NEWS_COLLECTOR:
        try:
            print("Using full news_collector...")
            collector_init_db()
            collect_all_news()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_count = cursor.fetchone()[0]
            conn.close()
            
            return True, total_count, {"message": "Collection completed using news_collector"}
        except Exception as e:
            print(f"Error using news_collector: {e}")
    
    # Fallback to basic RSS collection
    print("Using basic RSS collection...")
    feeds = [
        {"url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
        {"url": "https://rss.etnews.com/Section902.xml", "source": "전자신문"},
        {"url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
        {"url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
        {"url": "https://www.engadget.com/rss.xml", "source": "Engadget"},
    ]
    
    all_articles = []
    for feed in feeds:
        articles = collect_from_rss(feed["url"], feed["source"])
        all_articles.extend(articles)
    
    if all_articles:
        stats = save_articles_to_db(all_articles)
        return True, len(all_articles), stats
    
    return False, 0, {}

# Enhanced news collection API
@app.post("/api/collect-news")
async def collect_news(background_tasks: BackgroundTasks):
    """Start news collection in background"""
    try:
        await ensure_db_initialized()
        background_tasks.add_task(run_background_collection)
        return {
            "message": "뉴스 수집을 시작했습니다.", 
            "status": "started",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting news collection: {e}")
        return {"message": f"오류: {str(e)}", "status": "error"}

async def run_background_collection():
    """Background news collection task"""
    try:
        logger.info("🚀 Starting background news collection")
        
        if ENHANCED_MODULES_AVAILABLE:
            result = await collect_news_async(max_feeds=15)  # Limit feeds for background
            logger.info(f"✅ Background collection completed: {result}")
        else:
            # Fallback collection
            logger.info("Using fallback collector")
            # Implement basic collection here if needed
            
    except Exception as e:
        logger.error(f"❌ Background collection error: {e}")

@app.post("/api/collect-news-now")
async def collect_news_now(
    max_feeds: Optional[int] = Query(None, description="Maximum number of feeds to process")
):
    """Immediate news collection with full response"""
    try:
        await ensure_db_initialized()
        
        if ENHANCED_MODULES_AVAILABLE:
            logger.info("🚀 Starting enhanced news collection")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, collector.collect_all_news, max_feeds)
            
            # Get updated statistics
            try:
                if db.db_type == "postgresql":
                    stats_query = "SELECT COUNT(*) as count FROM articles"
                    sources_query = "SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC"
                else:
                    stats_query = "SELECT COUNT(*) as count FROM articles"
                    sources_query = "SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC"
                
                stats_result = db.execute_query(stats_query)
                total_articles = stats_result[0]['count'] if stats_result else 0
                
                sources_result = db.execute_query(sources_query)
                by_source = {row['source']: row['count'] for row in sources_result}
                
                return {
                    "message": f"뉴스 수집 완료: {result['stats']['total_inserted']}개 신규, {result['stats']['total_updated']}개 업데이트",
                    "status": "success",
                    "duration": result['duration'],
                    "processed": result['stats']['total_processed'],
                    "inserted": result['stats']['total_inserted'],
                    "updated": result['stats']['total_updated'],
                    "skipped": result['stats']['total_skipped'],
                    "total_articles": total_articles,
                    "by_source": by_source,
                    "successful_feeds": result['successful_feeds'],
                    "failed_feeds": result['failed_feeds'],
                    "total_feeds": result['total_feeds'],
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as stats_e:
                logger.warning(f"Error getting stats: {stats_e}")
                return {
                    "message": "뉴스 수집 완료 (통계 오류)",
                    "status": "success",
                    "collection_result": result
                }
        else:
            # Fallback simple collection
            if SIMPLE_COLLECTOR_AVAILABLE:
                total_count, stats = collect_all_feeds()
                return {
                    "message": f"뉴스 수집 완료: {stats.get('inserted', 0)}개 신규 추가",
                    "status": "success",
                    "processed": total_count,
                    "inserted": stats.get('inserted', 0),
                    "skipped": stats.get('skipped', 0)
                }
            else:
                raise HTTPException(status_code=500, detail="No news collector available")
            
    except Exception as e:
        logger.error(f"❌ News collection error: {e}")
        raise HTTPException(status_code=500, detail=f"뉴스 수집 오류: {str(e)}")

@app.get("/api/collection-status")
async def get_collection_status():
    """Get current collection status and stats"""
    try:
        await ensure_db_initialized()
        
        if ENHANCED_MODULES_AVAILABLE:
            # Get database stats
            total_query = "SELECT COUNT(*) as count FROM articles"
            total_articles = db.execute_query(total_query)[0]['count']
            
            recent_query = """
                SELECT COUNT(*) as count FROM articles 
                WHERE created_at > %s
            """ if db.db_type == "postgresql" else """
                SELECT COUNT(*) as count FROM articles 
                WHERE created_at > datetime('now', '-1 day')
            """
            
            if db.db_type == "postgresql":
                params = (datetime.now() - timedelta(days=1),)
                recent_articles = db.execute_query(recent_query, params)[0]['count']
            else:
                recent_articles = db.execute_query(recent_query)[0]['count']
            
            sources_query = "SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC LIMIT 10"
            top_sources = db.execute_query(sources_query)
            
            return {
                "status": "active",
                "total_articles": total_articles,
                "recent_articles_24h": recent_articles,
                "top_sources": top_sources,
                "database_type": db.db_type,
                "enhanced_features": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "basic",
                "enhanced_features": False,
                "message": "기본 수집 모드"
            }
            
    except Exception as e:
        logger.error(f"Error getting collection status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 정적 파일 서빙 설정 (React 빌드 파일)
frontend_dist = Path(__file__).parent.parent / "frontend" / "news-app" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            return {"message": "Frontend not built. Please run 'npm run build' in frontend/news-app directory"}
else:
    @app.get("/")
    async def root():
        return {"message": "News API Server is running. Frontend not found."}

# 컬렉션 관리 API
@app.get("/api/collections")
async def get_collections():
    """모든 컬렉션 목록을 반환합니다."""
    try:
        ensure_db_initialized()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all collections
        cursor.execute("""
            SELECT c.id, c.name, c.rules, c.created_at, 
                   COUNT(ca.article_id) as article_count
            FROM collections c
            LEFT JOIN collection_articles ca ON c.id = ca.collection_id
            GROUP BY c.id
        """)
        
        collections = []
        for row in cursor.fetchall():
            collection = dict(row)
            collection['rules'] = json.loads(collection['rules']) if collection['rules'] else {}
            collection['count'] = collection['article_count']
            collections.append(collection)
        
        conn.close()
        return collections
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 조회 실패: {str(e)}")

@app.post("/api/collections")
async def create_collection(request: CollectionRequest):
    """새로운 컬렉션을 생성합니다."""
    try:
        ensure_db_initialized()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create the collection
        cursor.execute("""
            INSERT INTO collections (name, rules) VALUES (?, ?)
        """, (request.name, json.dumps(request.rules) if request.rules else None))
        
        collection_id = cursor.lastrowid
        
        # Add articles based on rules
        if request.rules and 'include_keywords' in request.rules:
            keywords = request.rules['include_keywords']
            keyword_filter = ' OR '.join([f"keywords LIKE '%{kw}%'" for kw in keywords])
            
            cursor.execute(f"""
                INSERT INTO collection_articles (collection_id, article_id)
                SELECT ?, id FROM articles 
                WHERE {keyword_filter}
            """, (collection_id,))
            
            added_count = cursor.rowcount
        else:
            added_count = 0
        
        conn.commit()
        conn.close()
        
        return {"message": f"컬렉션 '{request.name}' 생성 완료", "added_articles": added_count, "collection_id": collection_id}
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=f"컬렉션 '{request.name}'이 이미 존재합니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 생성 실패: {str(e)}")

# 키워드 추출 API  
@app.post("/api/extract-keywords/{article_id}")
async def extract_article_keywords(article_id: int):
    """특정 기사의 키워드를 추출합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, summary FROM articles WHERE id = ?", (article_id,))
        article = cursor.fetchone()
        
        if not article:
            raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
        
        text = f"{article['title']} {article['summary'] or ''}"
        keywords = extract_keywords(text)
        
        # 키워드 업데이트
        cursor.execute("UPDATE articles SET keywords = ? WHERE id = ?", 
                      (",".join(keywords), article_id))
        conn.commit()
        conn.close()
        
        return {"keywords": keywords, "message": "키워드 추출 완료"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"키워드 추출 실패: {str(e)}")

# 번역 API
@app.post("/api/translate/{article_id}")  
async def translate_article(article_id: int):
    """특정 기사를 번역합니다."""
    try:
        ensure_db_initialized()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        article = cursor.fetchone()
        
        if not article:
            raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
        
        article_dict = dict(article)
        
        # Simple translation using basic patterns (without external API)
        # This is a placeholder - in production, use proper translation API
        translated_title = article_dict['title']
        translated_summary = article_dict.get('summary', '')
        
        # Basic keyword-based translation hints
        translation_map = {
            'AI': '인공지능',
            'Machine Learning': '머신러닝',
            'Deep Learning': '딥러닝',
            'Cloud': '클라우드',
            'Security': '보안',
            'Data': '데이터',
            'API': 'API',
            'Web': '웹',
            'Mobile': '모바일',
            'Database': '데이터베이스'
        }
        
        # Check if article appears to be in English
        is_english = any(word in translated_title.lower() for word in ['the', 'and', 'or', 'is', 'to'])
        
        if is_english:
            # Apply basic translations for known terms
            for eng, kor in translation_map.items():
                if eng.lower() in translated_title.lower():
                    translated_title = f"{translated_title} ({kor} 관련)"
                    break
            
            article_dict['translated_title'] = translated_title
            article_dict['translated_summary'] = f"[자동 번역 미지원] {translated_summary[:100]}..."
            article_dict['is_translated'] = True
            message = "기본 번역 제공 (전문 번역 서비스는 API 키 설정 필요)"
        else:
            article_dict['is_translated'] = False
            message = "한국어 기사입니다"
        
        conn.close()
        
        return {"message": message, "article": article_dict}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"번역 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)






