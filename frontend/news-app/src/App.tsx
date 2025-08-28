// frontend/news-app/src/App.tsx (빌드 오류가 수정된 최종 버전)

import React, { useState, useEffect, useRef } from 'react';
import {
  Typography, Box, TextField, Select, MenuItem, FormControl, InputLabel,
  Alert, CircularProgress, Paper, Chip, Card, CardContent, Stack, Divider,
  Button, Tabs, Tab, IconButton, Grid, AppBar, Toolbar, Drawer, Switch,
  FormControlLabel, List, ListItem, ListItemText, Pagination, Tooltip,
} from '@mui/material';
import {
  Article as ArticleIcon, Favorite, FavoriteBorder, Analytics, Cloud, Search,
  Refresh, FilterList, OpenInNew, DarkMode, LightMode, AccessTime,
  Visibility, Category as CategoryIcon, Translate as TranslateIcon
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';

import { newsApi } from './api/newsApi';
import type { Article, KeywordStat, CategoryStat, NetworkData } from './api/newsApi';
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';
import { ColorPalette } from './components/ColorPalette';
import { useThemeProvider } from './hooks/useTheme';
import { calculateReadingTime, formatReadingTime } from './utils/readingTime';

function TabPanel(props: any) {
  const { children, value, index, ...other } = props;
  return <div role="tabpanel" hidden={value !== index} {...other}>{value === index && <Box sx={{ p: 3 }}>{children}</Box>}</div>;
}

function CategoryChart({ data }: { data: CategoryStat[] }) {
    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="category" width={120} tick={{ fontSize: 12 }} />
                <RechartsTooltip />
                <Bar dataKey="count" fill="#8884d8" name="기사 수" />
            </BarChart>
        </ResponsiveContainer>
    );
}

function ArticleCard({ article, onToggleFavorite }: { article: Article, onToggleFavorite: (id: number) => void }) {
  const readingTime = calculateReadingTime(article.summary || '');
  return (
    <Card sx={{ mb: 2, transition: '0.2s', '&:hover': { boxShadow: 6 }, borderRadius: 2 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box flexGrow={1} mr={2}>
            <Typography variant="h6" component="a" href={article.link} target="_blank" rel="noopener noreferrer" sx={{ textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}>
              {article.title} <OpenInNew fontSize="inherit" sx={{ opacity: 0.6 }}/>
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
              <Chip label={article.source} size="small" variant="outlined" />
              <Chip icon={<AccessTime fontSize="small" />} label={new Date(article.published).toLocaleDateString()} size="small" />
              <Chip icon={<Visibility fontSize="small" />} label={formatReadingTime(readingTime)} size="small" />
              {article.main_category && article.main_category !== '기타' && (
                <Chip icon={<CategoryIcon />} label={`${article.main_category} > ${article.sub_category}`} size="small" color="primary" variant="outlined" />
              )}
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              {article.summary?.substring(0, 250)}...
            </Typography>
            <Box sx={{ mt: 1.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {Array.isArray(article.keywords) && article.keywords.slice(0, 8).map(kw => <Chip key={kw} label={kw} size="small" />)}
            </Box>
          </Box>
          <Stack spacing={0.5}>
            <Tooltip title={article.is_favorite ? "즐겨찾기 해제" : "즐겨찾기 추가"}>
              <IconButton onClick={() => onToggleFavorite(article.id)} color={article.is_favorite ? "error" : "default"}>
                {/* [수정된 부분] JSX 문법 오류 수정 */}
                {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
              </IconButton>
            </Tooltip>
            <Tooltip title="번역 (기능 준비중)"><IconButton disabled><TranslateIcon /></IconButton></Tooltip>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function App() {
  const { isDarkMode, toggleTheme, theme } = useThemeProvider();
  const [tabValue, setTabValue] = useState(0);
  const [articles, setArticles] = useState<Article[]>([]);
  const [filteredArticles, setFilteredArticles] = useState<Article[]>([]);
  const [stats, setStats] = useState<any>({});
  const [keywordStats, setKeywordStats] = useState<KeywordStat[]>([]);
  const [categoryStats, setCategoryStats] = useState<CategoryStat[]>([]);
  const [networkData, setNetworkData] = useState<NetworkData>();
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);

  const [filters, setFilters] = useState({
    searchTerm: '',
    selectedSource: 'all',
    selectedCategory: 'all',
    favoritesOnly: false,
  });
  
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const [drawerOpen, setDrawerOpen] = useState(window.innerWidth >= 1024);

  const loadAllData = async () => {
    try {
      const [articlesData, keywordsData, categoriesData, network] = await Promise.all([
        newsApi.getArticles({ limit: 1000 }),
        newsApi.getKeywordStats(),
        newsApi.getCategoryStats(),
        newsApi.getKeywordNetwork(),
      ]);
      setArticles(articlesData);
      setKeywordStats(keywordsData);
      setCategoryStats(categoriesData);
      setNetworkData(network);
    } catch (error) {
      console.error("데이터 로드 실패:", error);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadAllData().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let tempArticles = articles
      .filter(a => filters.favoritesOnly ? a.is_favorite : true)
      .filter(a => filters.selectedSource === 'all' ? true : a.source === filters.selectedSource)
      .filter(a => filters.selectedCategory === 'all' ? true : a.main_category === filters.selectedCategory)
      .filter(a => {
        if (!filters.searchTerm) return true;
        const lower = filters.searchTerm.toLowerCase();
        return a.title.toLowerCase().includes(lower) || a.summary?.toLowerCase().includes(lower);
      });
    setFilteredArticles(tempArticles);
    setStats({ total: tempArticles.length });
    setCurrentPage(1);
  }, [articles, filters]);

  const handleCollectNews = async () => {
    setCollecting(true);
    try {
      const result = await newsApi.collectNewsNow();
      alert(`뉴스 수집 완료: ${result.inserted || 0}개 신규`);
      await loadAllData(); // 모든 데이터 새로고침
    } catch (error) {
      alert("뉴스 수집에 실패했습니다.");
    } finally {
      setCollecting(false);
    }
  };

  const handleToggleFavorite = async (articleId: number) => {
    const article = articles.find(a => a.id === articleId);
    if (!article) return;
    try {
      if (article.is_favorite) await newsApi.removeFavorite(articleId);
      else await newsApi.addFavorite(articleId);
      setArticles(articles.map(a => a.id === articleId ? { ...a, is_favorite: !a.is_favorite } : a));
    } catch (error) { console.error("즐겨찾기 변경 실패:", error); }
  };

  const sources = [...new Set(articles.map(a => a.source))].sort();
  const categories = [...new Set(articles.map(a => a.main_category).filter(Boolean) as string[])].sort();
  const paginatedArticles = filteredArticles.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h5" sx={{ flexGrow: 1, fontWeight: 'bold' }}>🗞️ 뉴스있슈~</Typography>
          <Tooltip title="테마 변경"><IconButton color="inherit" onClick={toggleTheme}>{isDarkMode ? <LightMode /> : <DarkMode />}</IconButton></Tooltip>
          <Tooltip title="뉴스 새로 수집"><IconButton color="inherit" onClick={handleCollectNews} disabled={collecting}>{collecting ? <CircularProgress size={24} color="inherit"/> : <Refresh />}</IconButton></Tooltip>
          <Tooltip title="필터 메뉴"><IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}><FilterList /></IconButton></Tooltip>
        </Toolbar>
      </AppBar>
      
      <Box sx={{ display: 'flex', pt: '64px' }}>
        <Drawer variant="persistent" open={drawerOpen} sx={{ width: 300, flexShrink: 0, '& .MuiDrawer-paper': { width: 300, boxSizing: 'border-box', top: '64px', height: 'calc(100% - 64px)' }}}>
          <Box sx={{ p: 2, overflowY: 'auto' }}>
            <Typography variant="h6" gutterBottom>필터링</Typography>
            <Stack spacing={2}>
              <FormControl fullWidth><InputLabel>뉴스 출처</InputLabel><Select value={filters.selectedSource} label="뉴스 출처" onChange={e => setFilters(f => ({...f, selectedSource: e.target.value}))}><MenuItem value="all">전체</MenuItem>{sources.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}</Select></FormControl>
              <FormControl fullWidth><InputLabel>대분류</InputLabel><Select value={filters.selectedCategory} label="대분류" onChange={e => setFilters(f => ({...f, selectedCategory: e.target.value}))}><MenuItem value="all">전체</MenuItem>{categories.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}</Select></FormControl>
              <TextField fullWidth label="키워드 검색" value={filters.searchTerm} onChange={e => setFilters(f => ({...f, searchTerm: e.target.value}))} />
              <FormControlLabel control={<Switch checked={filters.favoritesOnly} onChange={e => setFilters(f => ({...f, favoritesOnly: e.target.checked}))}/>} label="즐겨찾기만 보기"/>
              <Divider />
              <Typography variant="body2">총 {articles.length}개 기사 중 {stats.total}개 표시</Typography>
            </Stack>
          </Box>
        </Drawer>

        <Box component="main" sx={{ flexGrow: 1, p: 3, ml: drawerOpen ? '300px' : 0, transition: 'margin-left 0.3s' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tab label="뉴스 목록" /> <Tab label="분석" /> <Tab label="테마" />
          </Tabs>

          {loading ? <CircularProgress /> :
            <>
              <TabPanel value={tabValue} index={0}>
                {paginatedArticles.length > 0 ? paginatedArticles.map(article => <ArticleCard key={article.id} article={article} onToggleFavorite={handleToggleFavorite} />) : <Alert severity="info">표시할 뉴스가 없습니다.</Alert>}
                {Math.ceil(filteredArticles.length / itemsPerPage) > 1 && <Pagination count={Math.ceil(filteredArticles.length / itemsPerPage)} page={currentPage} onChange={(_, page) => setCurrentPage(page)} sx={{ mt: 2, display: 'flex', justifyContent: 'center' }} />}
              </TabPanel>
              <TabPanel value={tabValue} index={1}>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}><Paper sx={{ p: 2 }}><Typography variant="h6">인기 키워드</Typography><List dense>{keywordStats.slice(0, 15).map(s => <ListItem key={s.keyword}><ListItemText primary={s.keyword} secondary={`${s.count}회`} /></ListItem>)}</List></Paper></Grid>
                  <Grid item xs={12} md={6}><Paper sx={{ p: 2 }}><Typography variant="h6">카테고리별 기사 수</Typography>{categoryStats.length > 0 ? <CategoryChart data={categoryStats} /> : <Alert severity="info">데이터 없음</Alert>}</Paper></Grid>
                  <Grid item xs={12}><KeywordNetwork data={networkData} /></Grid>
                </Grid>
              </TabPanel>
              <TabPanel value={tabValue} index={2}><ColorPalette /></TabPanel>
            </>
          }
        </Box>
      </Box>
    </ThemeProvider>
  );
}


