import axios from 'axios';
//import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: "https://streamlit-04-j6ho.onrender.com",
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
  summary?: string;
  keywords?: string | string[];
  created_at?: string;
  is_favorite: boolean;
}

export interface KeywordStats {
  keyword: string;
  count: number;
}

export interface NetworkData {
  nodes: Array<{
    id: string;
    label: string;
    value: number;
  }>;
  edges: Array<{
    from: string;
    to: string;
    value: number;
  }>;
}

export interface Stats {
  total_articles: number;
  total_sources: number;
  total_favorites: number;
  daily_counts: Array<{
    date: string;
    count: number;
  }>;
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
    const response = await api.get<KeywordStats[]>('/api/keywords/stats', {
      params: { limit },
    });
    return response.data;
  },

  getKeywordNetwork: async (limit = 30) => {
    const response = await api.get<NetworkData>('/api/keywords/network', {
      params: { limit },
    });
    return response.data;
  },

  getFavorites: async () => {
    const response = await api.get<Article[]>('/api/favorites');
    return response.data;
  },

  addFavorite: async (articleId: number) => {
    const response = await api.post('/api/favorites/add', {
      article_id: articleId,
    });
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

  // Enhanced news collection
  collectNews: async (days: number = 30, maxPages: number = 5) => {
    const response = await api.post('/api/collect-news', {
      days,
      max_pages: maxPages,
    });
    return response.data;
  },

  // Immediate news collection with full response and error handling
  collectNewsNow: async (maxFeeds?: number) => {
    try {
      const params = maxFeeds ? { max_feeds: maxFeeds } : {};
      console.log('📡 API call: /api/collect-news-now with params:', params);
      
      const response = await api.post('/api/collect-news-now', null, { 
        params,
        timeout: 60000 // 60 second timeout for collection
      });
      
      console.log('📡 API response:', response.data);
      return response.data;
    } catch (error) {
      console.error('API Error in collectNewsNow:', error);
      
      if (error.response) {
        // Server responded with error status
        const errorData = error.response.data;
        throw new Error(`Server Error (${error.response.status}): ${errorData.detail || errorData.message || 'Unknown error'}`);
      } else if (error.request) {
        // Network error
        throw new Error('Network Error: Unable to reach the server. Please check your connection.');
      } else {
        // Other errors
        throw new Error(`Request Error: ${error.message}`);
      }
    }
  },

  // Get collection status
  getCollectionStatus: async () => {
    const response = await api.get('/api/collection-status');
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

  extractKeywords: async (articleId: number) => {
    const response = await api.post(`/api/extract-keywords/${articleId}`);
    return response.data;
  },

  translateArticle: async (articleId: number) => {
    const response = await api.post(`/api/translate/${articleId}`);
    return response.data;
  },

};
