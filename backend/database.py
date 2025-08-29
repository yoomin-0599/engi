#backend/database.py (카테고리 기능이 추가된 최종 버전)
# backend/database.py (모든 기능이 포함된 최종 버전)

import os
import sqlite3
import json
import logging
from typing import Dict, List, Optional
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Render의 임시 저장소 경로를 기본값으로 사용
SQLITE_PATH = os.getenv("SQLITE_PATH", "/tmp/news.db")

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        # 데이터베이스 파일이 위치할 디렉토리가 없으면 생성합니다.
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()

    def get_connection(self):
        """데이터베이스 연결을 생성합니다."""
        conn = sqlite3.connect(self.db_path)
        # 결과를 사전(dict) 형태로 받기 위해 row_factory를 설정합니다.
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """SELECT 쿼리를 실행하고 결과를 dict 리스트로 반환합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """INSERT, UPDATE, DELETE 쿼리를 실행하고 영향을 받은 행의 수를 반환합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def init_database(self):
        """데이터베이스 테이블을 생성하고 초기화합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # [수정] 카테고리, 번역 필드 추가
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,
                published TEXT,
                source TEXT,
                summary TEXT,
                raw_text TEXT,
                keywords TEXT,
                language TEXT,
                main_category TEXT,
                sub_category TEXT,
                translated_title TEXT,
                translated_summary TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                article_id INTEGER PRIMARY KEY,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """)
            logger.info("✅ Database initialized successfully.")

    def insert_or_update_article(self, article: Dict) -> str:
        """기사가 존재하면 업데이트하고, 없으면 삽입합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM articles WHERE link = ?", (article['link'],))
            existing = cursor.fetchone()

            keywords_json = json.dumps(article.get('keywords', []))

            if existing:
                cursor.execute("""
                    UPDATE articles SET title = ?, summary = ?, keywords = ?, main_category = ?, sub_category = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (article['title'], article['summary'], keywords_json, article['main_category'], article['sub_category'], existing['id']))
                return "updated"
            else:
                cursor.execute("""
                    INSERT INTO articles (title, link, published, source, summary, raw_text, keywords, language, main_category, sub_category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article['title'], article['link'], article['published'], article['source'],
                    article['summary'], article.get('raw_text', ''), keywords_json,
                    article.get('language', 'ko'), article['main_category'], article['sub_category']
                ))
                return "inserted"

    def get_articles_with_filters(self, **filters) -> List[Dict]:
        """모든 필터링 기능이 포함된 기사 조회 함수입니다."""
        query = """
            SELECT a.*, CASE WHEN f.article_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
            FROM articles a LEFT JOIN favorites f ON a.id = f.article_id
        """
        conditions = []
        params = []

        if filters.get('search'):
            conditions.append("(a.title LIKE ? OR a.summary LIKE ?)")
            params.extend([f"%{filters['search']}%", f"%{filters['search']}%"])
        if filters.get('source') and filters['source'] != 'all':
            conditions.append("a.source = ?")
            params.append(filters['source'])
        if filters.get('main_category') and filters['main_category'] != 'all':
            conditions.append("a.main_category = ?")
            params.append(filters['main_category'])
        if filters.get('date_from'):
            conditions.append("a.published >= ?")
            params.append(filters['date_from'])
        if filters.get('date_to'):
            conditions.append("a.published <= ?")
            params.append(filters['date_to'])
        if filters.get('favorites_only'):
            conditions.append("f.article_id IS NOT NULL")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.published DESC LIMIT ? OFFSET ?"
        params.extend([filters.get('limit', 100), filters.get('offset', 0)])

        articles = self.execute_query(query, tuple(params))
        for article in articles:
            # DB에 JSON 문자열로 저장된 keywords를 리스트로 변환
            if isinstance(article.get('keywords'), str):
                try: article['keywords'] = json.loads(article['keywords'])
                except: article['keywords'] = []
        return articles

    def get_keyword_stats(self, limit: int = 50) -> List[Dict]:
        """키워드 통계를 계산합니다."""
        all_keywords_str = self.execute_query("SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != '[]'")
        keyword_list = []
        for row in all_keywords_str:
            try: keyword_list.extend(json.loads(row['keywords']))
            except: continue
        
        counts = Counter(keyword_list)
        return [{"keyword": kw, "count": count} for kw, count in counts.most_common(limit)]

    def get_keyword_network_data(self, limit: int = 30) -> Dict:
        """키워드 네트워크 데이터를 생성합니다."""
        top_stats = self.get_keyword_stats(limit)
        top_keywords = {stat['keyword'] for stat in top_stats}
        nodes = [{"id": stat['keyword'], "label": stat['keyword'], "value": stat['count']} for stat in top_stats]
        
        co_occurrence = Counter()
        all_keywords_str = self.execute_query("SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != '[]'")
        for row in all_keywords_str:
            try:
                keywords = json.loads(row['keywords'])
                # 기사 내 키워드 쌍의 동시 등장 횟수를 계산
                for i in range(len(keywords)):
                    for j in range(i + 1, len(keywords)):
                        kw1, kw2 = sorted((keywords[i], keywords[j]))
                        if kw1 in top_keywords and kw2 in top_keywords:
                            co_occurrence[(kw1, kw2)] += 1
            except: continue
        
        # [수정] 한 번이라도 같이 나오면 연결선을 표시하도록 기준 완화
        edges = [{"source": k1, "target": k2, "value": count} for (k1, k2), count in co_occurrence.items() if count >= 1]
        return {"nodes": nodes, "edges": edges}

db = Database(SQLITE_PATH)
