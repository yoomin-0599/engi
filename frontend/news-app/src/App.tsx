// frontend/news-app/src/App.tsx (모든 기능이 복원되고 카테고리 기능이 추가된 최종 버전)

import React, { useState, useEffect, useRef } from 'react';
import {
  Typography, Box, TextField, Select, MenuItem, FormControl, InputLabel,
  Alert, CircularProgress, Paper, Chip, Card, CardContent, Stack, Divider,
  Button, Tabs, Tab, IconButton, Grid, AppBar, Toolbar, Drawer, Switch,
  FormControlLabel, List, ListItem, ListItemText, Pagination, Tooltip,
} from '@mui/material';
import {
  Article as ArticleIcon, Favorite, FavoriteBorder, Analytics, Cloud, Search,
  Refresh, FilterList, TrendingUp, OpenInNew, DarkMode, LightMode, AccessTime,
  Visibility, Category as CategoryIcon // Category 아이콘 추가
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';


import { newsApi } from './api/newsApi';
import type { Article, KeywordStat, CategoryStat } from './api/newsApi'; // CategoryStat 타입 추가
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';
import { ColorPalette } from './components/ColorPalette';
import { useThemeProvider } from './hooks/useTheme';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { calculateReadingTime, formatReadingTime } from './utils/readingTime';

// --- TabPanel 컴포넌트 ---
interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}
function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return <div role="tabpanel" hidden={value !== index}>{value === index && <Box sx={{ p: 3 }}>{children}</Box>}</div>;
}

// --- 카테고리 통계 차트 컴포넌트 ---
function CategoryChart({ data }: { data: CategoryStat[] }) {
    return (
        <ResponsiveContainer width="100%" height={400}>
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="category" width={120} tick={{ fontSize: 12 }} />
                <RechartsTooltip />
                <Legend />
                <Bar dataKey="count" fill="#8884d8" name="기사 수" />
            </BarChart>
        </ResponsiveContainer>
    );
}

// --- 개별 기사 카드 컴포넌트 (모든 기능 복원) ---
function ArticleCard({ article, onToggleFavorite }: { article: Article, onToggleFavorite: (id: number) => void }) {
  const readingTime = calculateReadingTime((article.title || '') + (article.summary || ''));
  
  return (
    <Card sx={{ mb: 2.5, transition: 'all 0.3s', '&:hover': { transform: 'translateY(-2px)', boxShadow: 8 }, borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" spacing={2} justifyContent="space-between">
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5, lineHeight: 1.4 }}>
              <a href={article.link} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: 'inherit' }}>
                {article.title}
                <OpenInNew fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', opacity: 0.7 }} />
              </a>
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Chip icon={<ArticleIcon fontSize="small" />} label={article.source} variant="outlined" size="small" color="primary" />
              <Chip icon={<AccessTime fontSize="small" />} label={new Date(article.published).toLocaleDateString('ko-KR')} variant="outlined" size="small" />
              <Chip icon={<Visibility fontSize="small" />} label={formatReadingTime(readingTime)} variant="outlined" size="small" color="secondary" />
              {/* [추가] 카테고리 정보 표시 */}
              {article.main_category && article.main_category !== '기타' && (
                <Chip icon={<CategoryIcon />} label={`${article.main_category} > ${article.sub_category}`} size="small" color="success" variant="outlined" />
              )}
            </Stack>
            {article.summary && (
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'text.secondary' }}>
                {article.summary.length > 200 ? `${article.summary.substring(0, 200)}...` : article.summary}
              </Typography>
            )}
            {article.keywords && (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {article.keywords.slice(0, 8).map((keyword: string, index: number) => (
                  <Chip key={index} label={keyword} size="small" />
                ))}
              </Box>
            )}
          </Box>
          <Stack spacing={1} alignItems="center">
            <Tooltip title={article.is_favorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}>
              <IconButton onClick={() => onToggleFavorite(article.id)} color={article.is_favorite ? "error" : "default"}>
                {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

// --- 메인 App 컴포넌트 ---
export default function App() {
  const { isDarkMode, toggleTheme, theme } = useThemeProvider();
  const [tabValue, setTabValue] = useState(0);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [filteredArticles, setFilteredArticles] = useState<Article[]>([]);
  const [keywordStats, setKeywordStats] = useState<KeywordStat[]>([]);
  const [categoryStats, setCategoryStats] = useState<CategoryStat[]>([]); // 카테고리 통계 상태 추가
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  
  // 필터 상태
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all'); // 카테고리 필터 상태 추가
  const [dateFrom, setDateFrom] = useState(() => { const d = new Date(); d.setDate(d.getDate() - 7); return d.toISOString().split('T')[0]; });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  const [drawerOpen, setDrawerOpen] = useState(window.innerWidth >= 1024);

  // 초기 데이터 로드
  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      try {
        const [articlesData, keywordsData, categoriesData] = await Promise.all([
          newsApi.getArticles({ limit: 1000 }), // 기사 수를 늘려 통계 정확도 향상
          newsApi.getKeywordStats(),
          newsApi.getCategoryStats(), // 카테고리 통계 데이터 로드
        ]);
        setArticles(articlesData);
        setKeywordStats(keywordsData);
        setCategoryStats(categoriesData);
      } catch (error) {
        console.error('초기 데이터 로드 실패:', error);
      } finally {
        setLoading(false);
      }
    };
    loadInitialData();
  }, []);

  // 필터 적용 로직 (모든 필터 통합)
  useEffect(() => {
    let filtered = articles
      .filter(article => favoritesOnly ? article.is_favorite : true)
      .filter(article => selectedSource === 'all' ? true : article.source === selectedSource)
      .filter(article => selectedCategory === 'all' ? true : article.main_category === selectedCategory)
      .filter(article => dateFrom ? new Date(article.published) >= new Date(dateFrom) : true)
      .filter(article => dateTo ? new Date(article.published) <= new Date(dateTo) : true)
      .filter(article => {
        if (!searchTerm) return true;
        const searchLower = searchTerm.toLowerCase();
        return (
          article.title?.toLowerCase().includes(searchLower) ||
          article.summary?.toLowerCase().includes(searchLower) ||
          article.keywords?.some(k => k.toLowerCase().includes(searchLower))
        );
      });

    setFilteredArticles(filtered);
    setCurrentPage(1);
  }, [articles, searchTerm, selectedSource, selectedCategory, dateFrom, dateTo, favoritesOnly]);

  const handleCollectNews = async () => {
    setCollecting(true);
    try {
      const result = await newsApi.collectNewsNow();
      alert(`뉴스 수집 완료: ${result.inserted || 0}개 신규, ${result.updated || 0}개 업데이트`);
      // 모든 데이터 새로고침
      const [articlesData, keywordsData, categoriesData] = await Promise.all([
        newsApi.getArticles({ limit: 1000 }),
        newsApi.getKeywordStats(),
        newsApi.getCategoryStats(),
      ]);
      setArticles(articlesData);
      setKeywordStats(keywordsData);
      setCategoryStats(categoriesData);
    } catch (error) {
      console.error('뉴스 수집 실패:', error);
      alert('뉴스 수집 중 오류가 발생했습니다.');
    } finally {
      setCollecting(false);
    }
  };

  const handleToggleFavorite = async (articleId: number) => {
    try {
      const article = articles.find(a => a.id === articleId);
      if (!article) return;
      if (article.is_favorite) {
        await newsApi.removeFavorite(articleId);
      } else {
        await newsApi.addFavorite(articleId);
      }
      setArticles(prev => prev.map(a => a.id === articleId ? { ...a, is_favorite: !a.is_favorite } : a));
    } catch (error) {
      console.error('즐겨찾기 변경 실패:', error);
    }
  };

  useKeyboardShortcuts({
    onRefresh: handleCollectNews,
    onToggleTheme: toggleTheme,
    onSearch: () => searchInputRef.current?.focus(),
  });

  const sources = [...new Set(articles.map(a => a.source))].sort();
  const categories = [...new Set(articles.map(a => a.main_category).filter(Boolean) as string[])].sort();
  const totalPages = Math.ceil(filteredArticles.length / itemsPerPage);
  const currentArticles = filteredArticles.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>🗞️ 뉴스있슈~</Typography>
          <Tooltip title={isDarkMode ? '라이트 모드' : '다크 모드'}><IconButton color="inherit" onClick={toggleTheme}>{isDarkMode ? <LightMode /> : <DarkMode />}</IconButton></Tooltip>
          <Tooltip title="뉴스 새로 수집"><IconButton color="inherit" onClick={handleCollectNews} disabled={collecting}>{collecting ? <CircularProgress size={24} color="inherit"/> : <Refresh />}</IconButton></Tooltip>
          <Tooltip title="필터 메뉴"><IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}><FilterList /></IconButton></Tooltip>
        </Toolbar>
      </AppBar>
      
      <Box sx={{ display: 'flex' }}>
        <Drawer variant="persistent" open={drawerOpen} sx={{ width: 300, flexShrink: 0, '& .MuiDrawer-paper': { width: 300, boxSizing: 'border-box', pt: '64px' }}}>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>🔧 필터링</Typography>
            <Stack spacing={2}>
              <FormControl fullWidth><InputLabel>뉴스 출처</InputLabel><Select value={selectedSource} label="뉴스 출처" onChange={(e) => setSelectedSource(e.target.value)}><MenuItem value="all">전체</MenuItem>{sources.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}</Select></FormControl>
              <FormControl fullWidth><InputLabel>대분류</InputLabel><Select value={selectedCategory} label="대분류" onChange={(e) => setSelectedCategory(e.target.value)}><MenuItem value="all">전체</MenuItem>{categories.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}</Select></FormControl>
              <TextField fullWidth inputRef={searchInputRef} label="키워드 검색" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} InputProps={{startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />}}/>
              <TextField fullWidth type="date" label="시작일" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} InputLabelProps={{ shrink: true }}/>
              <TextField fullWidth type="date" label="종료일" value={dateTo} onChange={(e) => setDateTo(e.target.value)} InputLabelProps={{ shrink: true }}/>
              <FormControlLabel control={<Switch checked={favoritesOnly} onChange={(e) => setFavoritesOnly(e.target.checked)}/>} label="즐겨찾기만 보기"/>
            </Stack>
          </Box>
        </Drawer>

        <Box component="main" sx={{ flexGrow: 1, p: 3, mt: '64px', ml: drawerOpen ? '300px' : 0, transition: 'margin-left 0.3s' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tab icon={<ArticleIcon />} label="뉴스 목록" />
            <Tab icon={<Analytics />} label="키워드/카테고리 분석" />
            <Tab icon={<Cloud />} label="워드클라우드" />
            <Tab icon={<Favorite />} label="즐겨찾기" />
            <Tab icon={<DarkMode />} label="테마 설정" />
          </Tabs>

          {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box> :
            <>
              <TabPanel value={tabValue} index={0}>
                {currentArticles.length > 0 ? currentArticles.map(article => <ArticleCard key={article.id} article={article} onToggleFavorite={handleToggleFavorite} />) : <Alert severity="info">표시할 뉴스가 없습니다.</Alert>}
                {totalPages > 1 && <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}><Pagination count={totalPages} page={currentPage} onChange={(_, page) => setCurrentPage(page)} color="primary" /></Box>}
              </TabPanel>
              <TabPanel value={tabValue} index={1}>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}><Paper sx={{ p: 2 }}><Typography variant="h6">🔥 인기 키워드</Typography><List dense>{keywordStats.slice(0, 20).map(s => <ListItem key={s.keyword}><ListItemText primary={s.keyword} secondary={`${s.count}회`} /></ListItem>)}</List></Paper></Grid>
                  <Grid item xs={12} md={6}><Paper sx={{ p: 2 }}><Typography variant="h6">📊 카테고리별 기사 수</Typography>{categoryStats.length > 0 ? <CategoryChart data={categoryStats} /> : <Alert severity="info">카테고리 데이터가 없습니다.</Alert>}</Paper></Grid>
                  <Grid item xs={12}><Paper sx={{ p: 2, height: 500 }}><Typography variant="h6">🕸️ 키워드 관계 네트워크</Typography><KeywordNetwork /></Paper></Grid>
                </Grid>
              </TabPanel>
              <TabPanel value={tabValue} index={2}><Paper sx={{ p: 2, height: 600 }}><KeywordCloud keywords={keywordStats} /></Paper></TabPanel>
              <TabPanel value={tabValue} index={3}>
                {articles.filter(a => a.is_favorite).length > 0 ? articles.filter(a => a.is_favorite).map(article => <ArticleCard key={article.id} article={article} onToggleFavorite={handleToggleFavorite} />) : <Alert severity="info">즐겨찾기한 뉴스가 없습니다.</Alert>}
              </TabPanel>
              <TabPanel value={tabValue} index={4}><ColorPalette /></TabPanel>
            </>
          }
        </Box>
      </Box>
    </ThemeProvider>
  );
}


