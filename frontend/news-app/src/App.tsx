import React, { useState, useEffect, useRef } from 'react';
import {
  Typography,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Paper,
  Chip,
  Card,
  CardContent,
  Stack,
  Divider,
  Button,
  Tabs,
  Tab,
  IconButton,
  Grid,
  Container,
  AppBar,
  Toolbar,
  Drawer,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Pagination,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  Article as ArticleIcon,
  Favorite,
  FavoriteBorder,
  Analytics,
  Cloud,
  Search,
  Refresh,
  FilterList,
  TrendingUp,
  OpenInNew,
  DarkMode,
  LightMode,
  AccessTime,
  Keyboard,
  Visibility,
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { newsApi } from './api/newsApi';
import type { Article, KeywordStats } from './api/newsApi';
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';
import { ColorPalette } from './components/ColorPalette';
import { useThemeProvider } from './hooks/useTheme';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { calculateReadingTime, formatReadingTime } from './utils/readingTime';


interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// 개별 기사 카드 컴포넌트 (개선된 디자인)
interface ArticleCardProps {
  article: Article;
  onToggleFavorite: (id: number) => void;
  onExtractKeywords?: (id: number) => void;
  onTranslate?: (id: number) => void;
}

// 키워드 네트워크 컨테이너 컴포넌트
function KeywordNetworkContainer() {
  const [networkData, setNetworkData] = useState<any>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadNetworkData = async () => {
      try {
        const data = await newsApi.getKeywordNetwork();
        setNetworkData(data);
      } catch (error) {
        console.error('Failed to load network data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadNetworkData();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return <KeywordNetwork data={networkData} />;
}

function ArticleCard({ article, onToggleFavorite, onExtractKeywords, onTranslate }: ArticleCardProps) {
  const readingTime = calculateReadingTime((article.title || '') + (article.summary || ''));
  
  return (
    <Card sx={{ 
      mb: 2.5, 
      transition: 'all 0.3s ease-in-out', 
      '&:hover': { 
        transform: 'translateY(-2px)',
        boxShadow: '0 8px 25px rgba(0, 0, 0, 0.15)'
      },
      borderRadius: 3,
      overflow: 'hidden'
    }}>
      <CardContent sx={{ p: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={11}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ 
                  fontWeight: 700, 
                  mb: 1.5,
                  lineHeight: 1.4,
                  fontSize: { xs: '1.05rem', md: '1.15rem' }
                }}>
                  <a href={article.link} target="_blank" rel="noopener noreferrer" 
                     style={{ 
                       textDecoration: 'none', 
                       color: 'inherit'
                     }}>
                    {article.title}
                    <OpenInNew fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', opacity: 0.7 }} />
                  </a>
                </Typography>
              </Box>
            </Box>
            
            <Stack direction="row" spacing={{ xs: 1, md: 2 }} sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Chip
                icon={<ArticleIcon fontSize="small" />}
                label={article.source}
                variant="outlined"
                size="small"
                color="primary"
              />
              <Chip
                icon={<AccessTime fontSize="small" />}
                label={new Date(article.published).toLocaleDateString('ko-KR')}
                variant="outlined"
                size="small"
              />
              <Chip
                icon={<Visibility fontSize="small" />}
                label={formatReadingTime(readingTime)}
                variant="outlined"
                size="small"
                color="secondary"
              />
            </Stack>

            {article.summary && (
              <Typography variant="body1" sx={{ 
                mb: 2, 
                lineHeight: 1.7,
                color: 'text.secondary',
                fontSize: '0.95rem'
              }}>
                {article.summary.length > 200 
                  ? `${article.summary.substring(0, 200)}...` 
                  : article.summary}
              </Typography>
            )}

            {article.keywords && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" component="div" sx={{ mb: 1, fontWeight: 600 }}>
                  🏷️ 키워드
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {typeof article.keywords === 'string' 
                    ? article.keywords.split(',').slice(0, 8).map((keyword: string, index: number) => (
                        <Chip 
                          key={index} 
                          label={keyword.trim()} 
                          size="small"
                          variant="outlined"
                          sx={{ 
                            fontSize: '0.75rem',
                            height: 24,
                            borderRadius: 3,
                            '&:hover': {
                              backgroundColor: 'primary.main',
                              color: 'primary.contrastText',
                              borderColor: 'primary.main'
                            }
                          }} 
                        />
                      ))
                    : Array.isArray(article.keywords) 
                      ? article.keywords.slice(0, 8).map((keyword: string, index: number) => (
                          <Chip 
                            key={index} 
                            label={keyword} 
                            size="small"
                            variant="outlined"
                            sx={{ 
                              fontSize: '0.75rem',
                              height: 24,
                              borderRadius: 3,
                              '&:hover': {
                                backgroundColor: 'primary.main',
                                color: 'primary.contrastText',
                                borderColor: 'primary.main'
                              }
                            }} 
                          />
                        ))
                      : null
                  }
                </Box>
              </Box>
            )}
          </Grid>
          
          <Grid item xs={12} sm={1} sx={{ display: 'flex', justifyContent: { xs: 'flex-end', sm: 'center' } }}>
            <Stack spacing={1} alignItems="center">
              <Tooltip title={article.is_favorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}>
                <IconButton 
                  onClick={() => onToggleFavorite(article.id)}
                  color={article.is_favorite ? "secondary" : "default"}
                  sx={{
                    transition: 'all 0.2s',
                    '&:hover': {
                      transform: 'scale(1.1)'
                    }
                  }}
                >
                  {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
                </IconButton>
              </Tooltip>
              {onExtractKeywords && (
                <Tooltip title="키워드 추출">
                  <IconButton 
                    onClick={() => onExtractKeywords(article.id)}
                    size="small"
                  >
                    <TrendingUp fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              {onTranslate && (
                <Tooltip title="번역">
                  <IconButton 
                    onClick={() => onTranslate(article.id)}
                    size="small"
                  >
                    🌐
                  </IconButton>
                </Tooltip>
              )}
              <Typography variant="caption" color="text.secondary">
                #{article.id}
              </Typography>
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// 키보드 단축키 도움말 컴포넌트
function KeyboardShortcutsHelp() {
  return (
    <Paper sx={{ p: 2, mb: 2, bgcolor: 'action.hover' }}>
      <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
        ⌨️ 키보드 단축키
      </Typography>
      <Stack spacing={0.5}>
        <Typography variant="body2">• Ctrl/Cmd + R: 뉴스 새로고침</Typography>
        <Typography variant="body2">• Ctrl/Cmd + D: 다크모드 토글</Typography>
        <Typography variant="body2">• Ctrl/Cmd + K: 검색 포커스</Typography>
        <Typography variant="body2">• Ctrl/Cmd + ←/→: 탭 전환</Typography>
      </Stack>
    </Paper>
  );
}

// 메인 App 컴포넌트
export default function App() {
  const { isDarkMode, toggleTheme, theme, colors, ThemeContext } = useThemeProvider();
  const [tabValue, setTabValue] = useState(0);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [filteredArticles, setFilteredArticles] = useState<Article[]>([]);
  const [keywordStats, setKeywordStats] = useState<KeywordStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [collections, setCollections] = useState<any[]>([]);
  
  // 필터 상태
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [dateFrom, setDateFrom] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    return date.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  
  // 페이지네이션
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  // 사이드바 - 데스크톱에서는 항상 고정
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [showShortcutsHelp] = useState(false);
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);

  // 화면 크기 감지
  useEffect(() => {
    const handleResize = () => {
      const desktop = window.innerWidth >= 1024;
      setIsDesktop(desktop);
      // 데스크톱에서는 사이드바 항상 열기, 모바일에서는 기본으로 닫기
      if (desktop && !drawerOpen) {
        setDrawerOpen(true);
      } else if (!desktop && drawerOpen) {
        setDrawerOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // 초기 실행

    return () => window.removeEventListener('resize', handleResize);
  }, [drawerOpen]);

  // 초기 데이터 로드
  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      try {
        const articlesData = await newsApi.getArticles({ limit: 100 });
        setArticles(articlesData);
        const keywordStatsData = await newsApi.getKeywordStats();
        setKeywordStats(keywordStatsData);
        const collectionsData = await newsApi.getCollections();
        setCollections(collectionsData);
      } catch (error) {
        console.error('Failed to load initial data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  // 필터 적용
  useEffect(() => {
    let filtered = [...articles];

    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(article => 
        article.title?.toLowerCase().includes(searchLower) ||
        article.summary?.toLowerCase().includes(searchLower) ||
        (typeof article.keywords === 'string' 
          ? article.keywords.toLowerCase().includes(searchLower)
          : Array.isArray(article.keywords) 
            ? article.keywords.some(k => k.toLowerCase().includes(searchLower))
            : false)
      );
    }

    if (selectedSource && selectedSource !== 'all') {
      filtered = filtered.filter(article => article.source === selectedSource);
    }

    if (dateFrom) {
      filtered = filtered.filter(article => 
        new Date(article.published) >= new Date(dateFrom)
      );
    }

    if (dateTo) {
      filtered = filtered.filter(article => 
        new Date(article.published) <= new Date(dateTo)
      );
    }

    if (favoritesOnly) {
      filtered = filtered.filter(article => article.is_favorite);
    }

    // Sort by published date (newest first)
    filtered.sort((a, b) => 
      new Date(b.published).getTime() - new Date(a.published).getTime()
    );

    setFilteredArticles(filtered);
    setCurrentPage(1);
  }, [articles, searchTerm, selectedSource, dateFrom, dateTo, favoritesOnly]);

  // Enhanced news collection with improved error handling
  const collectNews = async () => {
    setCollecting(true);
    
    try {
      console.log('🚀 Starting news collection...');
      
      // Use the immediate collection API for better user feedback
      const collectionResult = await newsApi.collectNewsNow();
      
      console.log('✅ Collection completed:', collectionResult);
      
      if (collectionResult && collectionResult.status === 'success') {
        // Show success message with details
        const inserted = collectionResult.inserted || 0;
        const updated = collectionResult.updated || 0;
        const total = collectionResult.total_articles || 0;
        const duration = collectionResult.duration ? ` (${Math.round(collectionResult.duration)}초)` : '';
        
        const message = `✅ 뉴스 수집 완료${duration}\n` +
          `• 신규: ${inserted}개\n` + 
          `• 업데이트: ${updated}개\n` +
          `• 전체 기사: ${total}개`;
        
        alert(message);
        
        // Reload data with error handling for each request
        try {
          console.log('📰 Reloading articles...');
          const articlesData = await newsApi.getArticles({ limit: 100 });
          setArticles(articlesData);
          console.log(`✅ Loaded ${articlesData.length} articles`);
        } catch (articlesError) {
          console.error('Failed to reload articles:', articlesError);
        }
        
        try {
          console.log('🔍 Reloading keyword stats...');
          const keywordStatsData = await newsApi.getKeywordStats();
          setKeywordStats(keywordStatsData);
          console.log(`✅ Loaded ${keywordStatsData.length} keywords`);
        } catch (keywordsError) {
          console.error('Failed to reload keywords:', keywordsError);
        }
        
        // Update collections if they exist
        try {
          console.log('📁 Reloading collections...');
          const collectionsData = await newsApi.getCollections();
          setCollections(collectionsData);
          console.log(`✅ Loaded ${collectionsData.length} collections`);
        } catch (collectionsError) {
          console.warn('Collections not available:', collectionsError);
          // This is not critical, so don't show error to user
        }
        
      } else if (collectionResult) {
        console.error('Collection failed:', collectionResult);
        const errorMsg = collectionResult.message || 
          `뉴스 수집이 실패했습니다. 상태: ${collectionResult.status || 'unknown'}`;
        alert(`❌ ${errorMsg}`);
      } else {
        throw new Error('No response from collection API');
      }
      
    } catch (error) {
      console.error('Failed to collect news:', error);
      
      // More specific error messages
      let errorMessage = '뉴스 수집 중 오류가 발생했습니다.';
      
      if (error instanceof Error) {
        if (error.message.includes('fetch')) {
          errorMessage += '\n네트워크 연결을 확인해주세요.';
        } else if (error.message.includes('timeout')) {
          errorMessage += '\n요청 시간이 초과되었습니다.';
        } else {
          errorMessage += `\n오류 내용: ${error.message}`;
        }
      }
      
      errorMessage += '\n\n다시 시도해주세요.';
      alert(`❌ ${errorMessage}`);
      
    } finally {
      setCollecting(false);
      console.log('📝 Collection process finished');
    }
  };

  // 즐겨찾기 토글
  const handleToggleFavorite = async (articleId: number) => {
    try {
      const article = articles.find(a => a.id === articleId);
      if (!article) return;

      if (article.is_favorite) {
        await newsApi.removeFavorite(articleId);
      } else {
        await newsApi.addFavorite(articleId);
      }

      // 로컬 상태 업데이트
      setArticles(prev => prev.map(a => 
        a.id === articleId ? { ...a, is_favorite: !a.is_favorite } : a
      ));
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  // 컬렉션 생성
  const handleCreateCollection = async () => {
    const name = prompt('새 컬렉션 이름을 입력하세요:');
    if (!name) return;
    
    const keywords = prompt('관련 키워드를 쉼표로 구분하여 입력하세요 (예: AI, 클라우드, 보안):');
    const rules = keywords ? { include_keywords: keywords.split(',').map(k => k.trim()) } : {};
    
    try {
      await newsApi.createCollection(name, rules);
      const updatedCollections = await newsApi.getCollections();
      setCollections(updatedCollections);
      alert(`컬렉션 '${name}'이 생성되었습니다!`);
    } catch (error) {
      console.error('Failed to create collection:', error);
      alert('컬렉션 생성에 실패했습니다.');
    }
  };

  // 키워드 추출
  const handleExtractKeywords = async (articleId: number) => {
    try {
      const result = await newsApi.extractKeywords(articleId);
      // Update the article with new keywords
      setArticles(prev => prev.map(a => 
        a.id === articleId ? { ...a, keywords: result.keywords } : a
      ));
      alert('키워드 추출이 완료되었습니다!');
    } catch (error) {
      console.error('Failed to extract keywords:', error);
    }
  };

  // 번역
  const handleTranslate = async (articleId: number) => {
    try {
      const result = await newsApi.translateArticle(articleId);
      alert(result.message);
      if (result.article.is_translated) {
        // Update article with translation
        setArticles(prev => prev.map(a => 
          a.id === articleId ? { 
            ...a, 
            title: result.article.translated_title || a.title,
            summary: result.article.translated_summary || a.summary 
          } : a
        ));
      }
    } catch (error) {
      console.error('Failed to translate article:', error);
    }
  };

  // 탭 변경
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };


  // 키보드 단축키 설정
  useKeyboardShortcuts({
    onRefresh: collectNews,
    onToggleTheme: toggleTheme,
    onSearch: () => searchInputRef.current?.focus(),
    onNextTab: () => setTabValue(prev => (prev + 1) % 5),
    onPrevTab: () => setTabValue(prev => (prev - 1 + 5) % 5),
  });

  // 페이지네이션 계산
  const totalPages = Math.ceil(filteredArticles.length / itemsPerPage);
  const currentArticles = filteredArticles.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // 소스 목록 (articles에서 추출)
  const sources = [...new Set(articles.map(a => a.source))].sort();
  
  // 통계 (클라이언트 계산)
  const stats = {
    totalArticles: articles.length,
    totalSources: sources.length,
    totalFavorites: articles.filter(a => a.is_favorite).length,
    recentArticles: articles.filter(a => {
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return new Date(a.published) >= weekAgo;
    }).length
  };

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme, theme, colors }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
      
      {/* 상단 앱바 */}
      <AppBar position="fixed" sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            🗞️ 뉴스있슈~(News IT's Issue)
          </Typography>
          
          <Stack direction="row" spacing={1} sx={{ display: { xs: 'none', sm: 'flex' } }}>
            <Tooltip title={isDarkMode ? '라이트 모드' : '다크 모드'}>
              <IconButton color="inherit" onClick={toggleTheme}>
                {isDarkMode ? <LightMode /> : <DarkMode />}
              </IconButton>
            </Tooltip>
            
            <Tooltip title="새로고침">
              <IconButton 
                color="inherit" 
                onClick={collectNews}
                disabled={collecting}
              >
                <Refresh />
              </IconButton>
            </Tooltip>
            
            <Tooltip title={isDesktop ? "사이드바 토글" : "필터 메뉴"}>
              <IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}>
                <FilterList />
              </IconButton>
            </Tooltip>
          </Stack>
          
          {/* 모바일용 축약 버튼 */}
          <Stack direction="row" spacing={1} sx={{ display: { xs: 'flex', sm: 'none' } }}>
            <Tooltip title={isDarkMode ? '라이트 모드' : '다크 모드'}>
              <IconButton color="inherit" onClick={toggleTheme}>
                {isDarkMode ? <LightMode /> : <DarkMode />}
              </IconButton>
            </Tooltip>
            
            <Tooltip title="새로고침">
              <IconButton 
                color="inherit" 
                onClick={collectNews}
                disabled={collecting}
              >
                <Refresh />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="필터 메뉴">
              <IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}>
                <FilterList />
              </IconButton>
            </Tooltip>
          </Stack>
        </Toolbar>
      </AppBar>
      
      {/* 사이드바 (필터) */}
      <Drawer
        variant={isDesktop ? "persistent" : "temporary"}
        open={drawerOpen}
        onClose={() => !isDesktop && setDrawerOpen(false)}
        sx={{
          width: 300,
          flexShrink: 0,
          '& .MuiDrawer-paper': { 
            width: 300, 
            boxSizing: 'border-box', 
            pt: 8,
            ...(isDesktop && {
              position: 'fixed',
              height: '100vh',
            })
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          {showShortcutsHelp && <KeyboardShortcutsHelp />}
          
          <Typography variant="h6" gutterBottom>🔧 필터링</Typography>
          
          {/* 뉴스 소스 */}
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>뉴스 소스</InputLabel>
            <Select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              label="뉴스 소스"
            >
              <MenuItem value="all">전체</MenuItem>
              {sources.map(source => (
                <MenuItem key={source} value={source}>{source}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* 키워드 검색 */}
          <TextField
            fullWidth
            inputRef={searchInputRef}
            label="키워드 검색"
            placeholder="예: AI, 반도체, 5G (Ctrl+K)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          />

          {/* 기간 필터 */}
          <TextField
            fullWidth
            type="date"
            label="시작일"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            sx={{ mb: 2 }}
            InputLabelProps={{ shrink: true }}
          />
          
          <TextField
            fullWidth
            type="date"
            label="종료일"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            sx={{ mb: 2 }}
            InputLabelProps={{ shrink: true }}
          />

          {/* 즐겨찾기만 보기 */}
          <FormControlLabel
            control={
              <Switch
                checked={favoritesOnly}
                onChange={(e) => setFavoritesOnly(e.target.checked)}
              />
            }
            label="즐겨찾기만 보기"
            sx={{ mb: 2 }}
          />

          <Divider sx={{ my: 2 }} />
          
          {/* 데이터 관리 */}
          <Typography variant="h6" gutterBottom>📊 데이터 관리</Typography>
          
          <Button
            variant="contained"
            fullWidth
            startIcon={collecting ? <CircularProgress size={20} /> : <Refresh />}
            onClick={collectNews}
            disabled={collecting}
            sx={{ mb: 2 }}
          >
            {collecting ? '수집 중...' : '🔄 뉴스 수집'}
          </Button>

          {/* 컬렉션 관리 버튼 추가 */}
          <Button
            variant="outlined"
            fullWidth
            onClick={() => handleCreateCollection()}
            sx={{ mb: 2 }}
          >
            📁 새 컬렉션 만들기
          </Button>

          {/* 통계 */}
          <Paper sx={{ 
            p: 2, 
            bgcolor: theme => theme.palette.mode === 'dark' ? 'grey.800' : 'grey.50',
            border: theme => theme.palette.mode === 'dark' ? '1px solid rgba(255, 255, 255, 0.12)' : 'none',
            mb: 2
          }}>
            <Typography variant="body2" sx={{ 
              color: theme => theme.palette.mode === 'dark' ? 'grey.300' : 'text.primary'
            }}>
              📊 총 {stats.totalArticles}건의 뉴스<br/>
              📰 {stats.totalSources}개 소스<br/>
              ⭐ {stats.totalFavorites}개 즐겨찾기<br/>
              📅 최근 7일: {stats.recentArticles}건
            </Typography>
          </Paper>

          {/* 컬렉션 목록 */}
          {collections.length > 0 && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>📁 컬렉션</Typography>
              <Stack spacing={1}>
                {collections.map((collection, index) => (
                  <Chip
                    key={index}
                    label={`${collection.name} (${collection.count})`}
                    variant="outlined"
                    size="small"
                  />
                ))}
              </Stack>
            </>
          )}
        </Box>
      </Drawer>

      {/* 메인 컨텐츠 */}
      <Box sx={{ 
        flexGrow: 1, 
        p: { xs: 2, md: 3 }, 
        pt: { xs: 10, md: 12 },
        ml: (isDesktop && drawerOpen) ? '300px' : 0,
        transition: 'margin-left 0.3s',
        minHeight: '100vh'
      }}>
        <Typography variant="body1" sx={{ mb: 2, color: 'text.secondary' }}>
          **IT/공학 뉴스 수집, 분석, 시각화 대시보드**
        </Typography>

        {/* 탭 */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange}
            variant={isDesktop ? "standard" : "scrollable"}
            scrollButtons={isDesktop ? false : "auto"}
            sx={{
              '& .MuiTab-root': {
                minWidth: isDesktop ? 120 : 80,
                fontSize: { xs: '0.8rem', md: '0.875rem' }
              }
            }}
          >
            <Tab icon={<ArticleIcon />} label={isDesktop ? "📰 뉴스 목록" : "뉴스"} />
            <Tab icon={<Analytics />} label={isDesktop ? "📊 키워드 분석" : "분석"} />
            <Tab icon={<Cloud />} label={isDesktop ? "☁️ 워드클라우드" : "워드클라우드"} />
            <Tab icon={<Favorite />} label={isDesktop ? "⭐ 즐겨찾기" : "즐겨찾기"} />
            <Tab icon={<DarkMode />} label={isDesktop ? "🎨 테마/컬러" : "테마"} />
          </Tabs>
        </Box>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* 뉴스 목록 탭 */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h5" gutterBottom>📰 뉴스 목록</Typography>
          <Typography variant="body1" sx={{ mb: 2, fontWeight: 'bold' }}>
            **총 {filteredArticles.length}건의 뉴스**
          </Typography>

          {filteredArticles.length === 0 ? (
            <Alert severity="info">
              {articles.length === 0 ? 
                '데이터가 없습니다. 사이드바에서 "뉴스 수집" 버튼을 클릭하여 데이터를 수집하세요.' :
                '필터 조건에 맞는 뉴스가 없습니다.'
              }
            </Alert>
          ) : (
            <>
              {currentArticles.map(article => (
                <ArticleCard
                  key={article.id}
                  article={article}
                  onToggleFavorite={handleToggleFavorite}
                  onExtractKeywords={handleExtractKeywords}
                  onTranslate={handleTranslate}
                />
              ))}
              
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={(_, page) => setCurrentPage(page)}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </TabPanel>

        {/* 키워드 분석 탭 */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h5" gutterBottom>📊 키워드 네트워크 분석</Typography>
          
          {keywordStats.length === 0 ? (
            <Alert severity="info">분석할 데이터가 없습니다.</Alert>
          ) : (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>🔥 인기 키워드 TOP 20</Typography>
                <Paper sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
                  <List dense>
                    {keywordStats.slice(0, 20).map((stat, index) => (
                      <ListItem key={stat.keyword}>
                        <ListItemText
                          primary={`${index + 1}. ${stat.keyword}`}
                          secondary={`${stat.count}회`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>📈 키워드 분포</Typography>
                <Paper sx={{ p: 2, height: 400 }}>
                  {keywordStats.length > 0 && (
                    <KeywordCloud keywords={keywordStats.slice(0, 50)} />
                  )}
                </Paper>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>🕸️ 키워드 관계 네트워크</Typography>
                <Paper sx={{ p: 2, height: 500 }}>
                  <KeywordNetworkContainer />
                </Paper>
              </Grid>
            </Grid>
          )}
        </TabPanel>

        {/* 워드클라우드 탭 */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h5" gutterBottom>☁️ 워드클라우드</Typography>
          
          {keywordStats.length === 0 ? (
            <Alert severity="info">워드클라우드를 생성할 데이터가 없습니다.</Alert>
          ) : (
            <Paper sx={{ p: 2, height: 600 }}>
              <KeywordCloud keywords={keywordStats} />
            </Paper>
          )}
        </TabPanel>

        {/* 즐겨찾기 탭 */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h5" gutterBottom>⭐ 즐겨찾기</Typography>
          
          {(() => {
            const favorites = articles.filter(a => a.is_favorite);
            return favorites.length === 0 ? (
              <Alert severity="info">즐겨찾기한 뉴스가 없습니다.</Alert>
            ) : (
              <>
                <Typography variant="body1" sx={{ mb: 2, fontWeight: 'bold' }}>
                  **총 {favorites.length}건의 즐겨찾기**
                </Typography>
                {favorites.map(article => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    onToggleFavorite={handleToggleFavorite}
                    onExtractKeywords={handleExtractKeywords}
                    onTranslate={handleTranslate}
                  />
                ))}
              </>
            );
          })()}
        </TabPanel>

        {/* 테마/컬러 팔레트 탭 */}
        <TabPanel value={tabValue} index={4}>
          <Typography variant="h5" gutterBottom>🎨 테마 & 컬러 팔레트</Typography>
          <ColorPalette />
        </TabPanel>
      </Box>
      </ThemeProvider>
    </ThemeContext.Provider>
  );
}

