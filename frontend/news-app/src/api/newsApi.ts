// frontend/news-app/src/api/newsApi.ts (모든 기능이 포함된 최종 버전)

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
  summary?: string;
  keywords?: string[];
  main_category?: string;
  sub_category?: string;
  is_favorite: boolean;
}

export interface KeywordStat { keyword: string; count: number; }
export interface CategoryStat { category: string; count: number; }
export interface NetworkData {
  nodes: Array<{ id: string; label: string; value: number }>;
  edges: Array<{ source: string; target: string; value: number }>;
}
export interface Stats { total_articles: number; total_sources: number; total_favorites: number; }
export interface Collection { name: string; count: number; }

export const newsApi = {
  getArticles: async (params?: object) => {
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
  getCategoryStats: async () => {
    const response = await api.get<CategoryStat[]>('/api/categories/stats');
    return response.data;
  },
  getFavorites: async () => {
    const response = await api.get<Article[]>('/api/favorites');
    return response.data;
  },
  addFavorite: async (articleId: number) => {
    return await api.post('/api/favorites/add', { article_id: articleId });
  },
  removeFavorite: async (articleId: number) => {
    return await api.delete(`/api/favorites/${articleId}`);
  },
  getStats: async () => {
    const response = await api.get<Stats>('/api/stats');
    return response.data;
  },
  collectNewsNow: async () => {
    const response = await api.post('/api/collect-news-now', null, { timeout: 180000 });
    return response.data;
  },
};
  
  getCollections: async () => {
    const response = await api.get<Collection[]>('/api/collections');
    return response.data;
  },

  createCollection: async (name: string, rules: Record<string, any> = {}) => {
    const response = await api.post('/api/collections', { name, rules });
    return response.data;
  },
};



