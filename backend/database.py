# backend/database.py

import json
import logging
import os
import sqlite3
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Render의 임시 저장소 또는 로컬 경로 사용
DB_PATH = os.getenv("SQLITE_PATH", "news.db")

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        # 데이터베이스 파일이 위치할 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self):
        """데이터베이스 연결을 생성하고 반환합니다."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 결과를 딕셔너리처럼 사용할 수 있게 설정
        return conn

    def init_database(self):
        """필요한 모든 테이블을 생성합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # 기사 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    link TEXT UNIQUE NOT NULL,
                    published TEXT,
                    source TEXT,
                    summary TEXT,
                    keywords TEXT, -- 키워드를 JSON 문자열로 저장
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            # 즐겨찾기 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    article_id INTEGER UNIQUE,
                    FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def insert_or_update_article(self, article: Dict) -> str:
        """기사가 존재하면 업데이트하고, 없으면 새로 추가합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM articles WHERE link = ?", (article['link'],))
            existing = cursor.fetchone()

            keywords_json = json.dumps(article.get('keywords', []))

            if existing:
                # 기존 기사 업데이트 (제목, 요약, 키워드)
                cursor.execute("""
                    UPDATE articles SET title = ?, summary = ?, keywords = ?
                    WHERE id = ?
                """, (article['title'], article['summary'], keywords_json, existing['id']))
                result = "updated"
            else:
                # 새 기사 추가
                cursor.execute("""
                    INSERT INTO articles (title, link, published, source, summary, keywords)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    article['title'], article['link'], article['published'],
                    article['source'], article['summary'], keywords_json
                ))
                result = "inserted"
            
            conn.commit()
            return result
        finally:
            conn.close()

    def get_articles_with_filters(self, limit: int, offset: int, **filters) -> List[Dict]:
        """다양한 조건으로 기사를 필터링하여 조회합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT a.*, CASE WHEN f.article_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
                FROM articles a
                LEFT JOIN favorites f ON a.id = f.article_id
            """
            conditions = []
            params = []

            if filters.get('favorites_only'):
                conditions.append("f.article_id IS NOT NULL")
            
            if filters.get('source'):
                conditions.append("a.source = ?")
                params.append(filters['source'])
            
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                conditions.append("(a.title LIKE ? OR a.summary LIKE ? OR a.keywords LIKE ?)")
                params.extend([search_term, search_term, search_term])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY a.published DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            articles = []
            for row in cursor.fetchall():
                article = dict(row)
                # JSON 문자열로 저장된 키워드를 리스트로 변환
                if article.get('keywords'):
                    try:
                        article['keywords'] = json.loads(article['keywords'])
                    except json.JSONDecodeError:
                        article['keywords'] = [] # 파싱 실패 시 빈 리스트
                articles.append(article)
            return articles
        finally:
            conn.close()

    def get_all_sources(self) -> List[str]:
        """모든 뉴스 출처 목록을 조회합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT source FROM articles ORDER BY source")
            return [row['source'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_keyword_stats(self, limit: int) -> List[Dict]:
        """키워드 등장 빈도 통계를 계산합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != '[]'")
            
            keyword_counts = {}
            for row in cursor.fetchall():
                try:
                    keywords = json.loads(row['keywords'])
                    for keyword in keywords:
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            sorted_keywords = sorted(keyword_counts.items(), key=lambda item: item[1], reverse=True)
            return [{"keyword": k, "count": v} for k, v in sorted_keywords[:limit]]
        finally:
            conn.close()

    def get_keyword_network_data(self, limit: int) -> Dict:
        """키워드 관계 네트워크 데이터를 생성합니다."""
        stats = self.get_keyword_stats(limit)
        top_keywords = {stat['keyword'] for stat in stats}
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != '[]'")
            
            co_occurrence = {}
            for row in cursor.fetchall():
                try:
                    keywords = json.loads(row['keywords'])
                    # 상위 키워드에 포함된 것들만 필터링
                    filtered_keywords = [kw for kw in keywords if kw in top_keywords]
                    for i in range(len(filtered_keywords)):
                        for j in range(i + 1, len(filtered_keywords)):
                            pair = tuple(sorted((filtered_keywords[i], filtered_keywords[j])))
                            co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            nodes = [{"id": stat['keyword'], "label": stat['keyword'], "value": stat['count']} for stat in stats]
            edges = [{"source": pair[0], "target": pair[1], "value": weight} for pair, weight in co_occurrence.items() if weight > 1] # 최소 2번 이상 함께 등장
            
            return {"nodes": nodes, "edges": edges}
        finally:
            conn.close()

    def add_favorite(self, article_id: int):
        """즐겨찾기를 추가합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO favorites (article_id) VALUES (?)", (article_id,))
            conn.commit()
        finally:
            conn.close()

    def remove_favorite(self, article_id: int):
        """즐겨찾기를 제거합니다."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
            conn.commit()
        finally:
            conn.close()

# 다른 파일에서 쉽게 사용할 수 있도록 인스턴스 생성
db = Database(DB_PATH)
