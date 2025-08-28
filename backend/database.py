# backend/database.py (모든 기능이 포함된 최종 버전)

import json
import logging
import os
import sqlite3
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("SQLITE_PATH", "news.db")

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self):
        """데이터베이스 연결을 생성하고 반환합니다."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """[복원된 함수] SELECT 쿼리를 실행하고 결과를 딕셔너리 리스트로 반환합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        finally:
            conn.close()

    def init_database(self):
        """프로젝트에 필요한 모든 테이블을 생성합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL, link TEXT UNIQUE NOT NULL, published TEXT,
                    source TEXT, summary TEXT, keywords TEXT, raw_text TEXT,
                    category TEXT, language TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    article_id INTEGER UNIQUE,
                    FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            logger.info("✅ 데이터베이스 테이블이 준비되었습니다.")
        finally:
            conn.close()

    def insert_or_update_article(self, article: Dict) -> str:
        """기사가 이미 존재하면 업데이트하고, 없으면 새로 추가합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM articles WHERE link = ?", (article['link'],))
            existing = cursor.fetchone()
            keywords_json = json.dumps(article.get('keywords', []))

            if existing:
                cursor.execute("""
                    UPDATE articles SET title = ?, summary = ?, keywords = ?, raw_text = ?
                    WHERE id = ?
                """, (article['title'], article['summary'], keywords_json, article.get('raw_text', ''), existing['id']))
                result = "updated"
            else:
                cursor.execute("""
                    INSERT INTO articles (title, link, published, source, summary, keywords, raw_text, category, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article['title'], article['link'], article['published'],
                    article['source'], article['summary'], keywords_json,
                    article.get('raw_text', ''), article.get('category', ''), article.get('language', '')
                ))
                result = "inserted"
            conn.commit()
            return result
        finally:
            conn.close()

    def get_articles_with_filters(self, limit: int, offset: int, **filters) -> List[Dict]:
        """모든 조건으로 기사를 필터링하여 조회합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT a.*, CASE WHEN f.article_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite FROM articles a LEFT JOIN favorites f ON a.id = f.article_id"
            conditions, params = [], []

            if filters.get('favorites_only'): conditions.append("f.article_id IS NOT NULL")
            if filters.get('source'): conditions.append("a.source = ?"); params.append(filters['source'])
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                conditions.append("(a.title LIKE ? OR a.summary LIKE ? OR a.keywords LIKE ?)")
                params.extend([search_term, search_term, search_term])

            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY a.published DESC LIMIT ? OFFSET ?"; params.extend([limit, offset])

            cursor.execute(query, params)
            articles = []
            for row in cursor.fetchall():
                article = dict(row)
                if article.get('keywords'):
                    try: article['keywords'] = json.loads(article['keywords'])
                    except: article['keywords'] = []
                articles.append(article)
            return articles
        finally:
            conn.close()

    def get_all_sources(self) -> List[str]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(); cursor.execute("SELECT DISTINCT source FROM articles WHERE source IS NOT NULL ORDER BY source")
            return [row['source'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_keyword_stats(self, limit: int) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(); cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != '[]'")
            keyword_counts = {}
            for row in cursor.fetchall():
                try:
                    keywords = json.loads(row['keywords'])
                    for keyword in keywords: keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                except: continue
            sorted_keywords = sorted(keyword_counts.items(), key=lambda item: item[1], reverse=True)
            return [{"keyword": k, "count": v} for k, v in sorted_keywords[:limit]]
        finally:
            conn.close()
            
    def get_keyword_network_data(self, limit: int) -> Dict:
        stats = self.get_keyword_stats(limit)
        top_keywords = {stat['keyword'] for stat in stats}
        conn = self.get_connection()
        try:
            cursor = conn.cursor(); cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != '[]'")
            co_occurrence = {}
            for row in cursor.fetchall():
                try:
                    keywords = json.loads(row['keywords'])
                    filtered_keywords = [kw for kw in keywords if kw in top_keywords]
                    for i in range(len(filtered_keywords)):
                        for j in range(i + 1, len(filtered_keywords)):
                            pair = tuple(sorted((filtered_keywords[i], filtered_keywords[j])))
                            co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
                except: continue
            nodes = [{"id": stat['keyword'], "label": stat['keyword'], "value": stat['count']} for stat in stats]
            edges = [{"source": pair[0], "target": pair[1], "value": weight} for pair, weight in co_occurrence.items() if weight > 1]
            return {"nodes": nodes, "edges": edges}
        finally:
            conn.close()

    def add_favorite(self, article_id: int):
        conn = self.get_connection();
        try:
            cursor = conn.cursor(); cursor.execute("INSERT OR IGNORE INTO favorites (article_id) VALUES (?)", (article_id,)); conn.commit()
        finally:
            conn.close()

    def remove_favorite(self, article_id: int):
        conn = self.get_connection()
        try:
            cursor = conn.cursor(); cursor.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,)); conn.commit()
        finally:
            conn.close()

db = Database(DB_PATH)


