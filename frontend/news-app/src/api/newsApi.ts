// frontend/news-app/src/api/newsApi.ts (모든 기능이 포함된 최종 버전)

import axios from 'axios';

// Netlify 환경 변수 또는 로컬 주소를 사용합니다.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- [수정] Article 타입에 카테고리 필드 추가 ---
export interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
  summary?: string;
  keywords?: string[]; // keywords는 문자열 배열로 통일
  main_category?: string; // 대분류 필드 추가
  sub_category?: string;  // 소분류 필드 추가
  is_favorite: boolean;
}

export interface KeywordStat {
  keyword: string;
  count: number;
}

// --- [추가] 카테고리 통계 타입 추가 ---
export interface CategoryStat {
    category: string;
    count: number;
}

export interface NetworkData {
  nodes: Array<{ id: string; label: string; value: number }>;
  edges: Array<{ source: string; target: string; value: number }>;
}

export interface Stats {
  total_articles: number;
  total_sources: number;
  total_favorites: number;
  daily_counts: Array<{ date: string; count: number }>;
}

export interface Collection {
  name: string;
  count: number;
  rules: Record<string, any>;
  articles: Article[];
}


export const newsApi = {
  getArticles: async (params?: {
    limit?: number;
    offset?: number;
    source?: string;
    search?: string;
    favorites_only?: boolean;
    date_from?: string;
    date_to?: string;
  }) => {
    const response = await api.get<Article[]>('/api/articles', { params });
    return response.data;
  },

  getSources: async () => {
    const response = await api.get<string[]>('/api/sources');
    return response.data;
  },

  getKeywordStats: async (limit = 50) => {
    const response = await api.get<KeywordStat[]>('/api/keywords/stats', { params: { limit } });
    return response.data;
  },
  
  getKeywordNetwork: async (limit = 30) => {
    const response = await api.get<NetworkData>('/api/keywords/network', { params: { limit } });
    return response.data;
  },

  // --- [추가] 카테고리 통계 API 호출 함수 ---
  getCategoryStats: async () => {
    const response = await api.get<CategoryStat[]>('/api/categories/stats');
    return response.data;
  },

  // --- [복원] 원래 코드에 있던 모든 기능 ---
  getFavorites: async () => {
    const response = await api.get<Article[]>('/api/favorites');
    return response.data;
  },

  addFavorite: async (articleId: number) => {
    const response = await api.post('/api/favorites/add', { article_id: articleId });
    return response.data;
  },

  removeFavorite: async (articleId: number) => {
    const response = await api.delete(`/api/favorites/${articleId}`);
    return response.data;
  },

  getStats: async () => {
    const response = await api.get<Stats>('/api/stats');
    return response.data;
  },

  collectNewsNow: async () => {
    // 뉴스 수집은 오래 걸릴 수 있으므로 타임아웃을 넉넉하게 3분으로 설정
    const response = await api.post('/api/collect-news-now', null, { timeout: 180000 });
    return response.data;
  },
  
  getCollections: async () => {
    const response = await api.get<Collection[]>('/api/collections');
    return response.data;
  },

  createCollection: async (name: string, rules: Record<string, any> = {}) => {
    const response = await api.post('/api/collections', { name, rules });
    return response.data;
  },
};


