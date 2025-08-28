// frontend/news-app/src/App.tsx (원래 UI/기능 + 신규 카테고리 기능이 통합된 최종 버전)

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
  Visibility, Category as CategoryIcon, Translate as TranslateIcon, TrendingUp
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';

import { newsApi } from './api/newsApi';
import type { Article, KeywordStat, CategoryStat, NetworkData, Stats, Collection } from './api/newsApi';
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';
import { ColorPalette } from './components/ColorPalette';
import { useThemeProvider } from './hooks/useTheme';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { calculateReadingTime, formatReadingTime } from './utils/readingTime';

function TabPanel(props: any) {
  const { children, value, index, ...other } = props;
  return <div role="tabpanel" hidden={value !== index} {...other}>{value === index && <Box sx={{ p: 3 }}>{children}</Box>}</div>;
}

function CategoryChart({ data }: { data: CategoryStat[] }) {
    return (
        <ResponsiveContainer width="100%" height={400}>
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

// [복원] 원래의 모든 기능을 가진 ArticleCard
function ArticleCard({ article, onToggleFavorite, onExtractKeywords, onTranslate }: {
  article: Article;
  onToggleFavorite: (id: number) => void;
  onExtractKeywords: (id: number) => void; // 기능 복원
  onTranslate: (id: number) => void; // 기능 복원
}) {
  const readingTime = calculateReadingTime(article.summary || '');
  return (
    <Card sx={{ mb: 2.5, transition: 'all 0.3s ease-in-out', '&:hover': { transform: 'translateY(-2px)', boxShadow: 8}, borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={11}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5, lineHeight: 1.4 }}>
              <a href={article.link} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: 'inherit' }}>
                {article.title} <OpenInNew fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', opacity: 0.7 }} />
              </a>
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Chip icon={<ArticleIcon fontSize="small" />} label={article.source} variant="outlined" size="small" color="primary" />
              <Chip icon={<AccessTime fontSize="small" />} label={new Date(article.published).toLocaleDateString('ko-KR')} variant="outlined" size="small" />
              <Chip icon={<Visibility fontSize="small" />} label={formatReadingTime(readingTime)} variant="outlined" size="small" color="secondary" />
              {article.main_category && article.main_category !== '기타' && (
                <Chip icon={<CategoryIcon />} label={`${article.main_category} > ${article.sub_category}`} size="small" color="success" variant="outlined" />
              )}
            </Stack>
            {article.summary && (
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'text.secondary' }}>
                {article.summary.length > 200 ? `${article.summary.substring(0, 200)}...` : article.summary}
              </Typography>
            )}
            {Array.isArray(article.keywords) && (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {article.keywords.slice(0, 8).map((keyword, index) => <Chip key={index} label={keyword} size="small" />)}
              </Box>
            )}
          </Grid>
          <Grid item xs={12} sm={1} sx={{ display: 'flex', justifyContent: { xs: 'flex-end', sm: 'center' } }}>
            <Stack spacing={1} alignItems="center">
              <Tooltip title={article.is_favorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}>
                <IconButton onClick={() => onToggleFavorite(article.id)} color={article.is_favorite ? "error" : "default"}>
                  {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
                </IconButton>
              </Tooltip>
              {/* [복원] 키워드 추출 및 번역 버튼 */}
              <Tooltip title="키워드 재추출"><IconButton onClick={() => onExtractKeywords(article.id)} size="small"><TrendingUp fontSize="small" /></IconButton></Tooltip>
              <Tooltip title="번역 (준비중)"><IconButton onClick={() => onTranslate(article.id)} size="small" disabled><TranslateIcon fontSize="small" /></IconButton></Tooltip>
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

export default function App() {
  const { isDarkMode, toggleTheme, theme } = useThemeProvider();
  const [tabValue, setTabValue] = useState(0);
  const [articles, setArticles] = useState<Article[]>([]);
  const [filteredArticles, setFilteredArticles] = useState<Article[]>([]);
  const [stats, setStats] = useState<Partial<Stats>>({});
  const [keywordStats, setKeywordStats] = useState<KeywordStat[]>([]);
  const [categoryStats, setCategoryStats] = useState<CategoryStat[]>([]);
  const [networkData, setNetworkData] = useState<NetworkData>();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);

  const [filters, setFilters] = useState({
    searchTerm: '',
    selectedSource: 'all',
    selectedCategory: 'all',
    favoritesOnly: false,
    dateFrom: (() => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().split('T')[0]; })(),
    dateTo: new Date().toISOString().split('T')[0],
  });
  
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const [drawerOpen, setDrawerOpen] = useState(window.innerWidth >= 1024);

  const loadAllData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const [articlesData, keywordsData, categoriesData, network, statsData, collectionsData] = await Promise.all([
        newsApi.getArticles({ limit: 1000 }),
        newsApi.getKeywordStats(),
        newsApi.getCategoryStats(),
        newsApi.getKeywordNetwork(),
        newsApi.getStats(),
        newsApi.getCollections(),
      ]);
      setArticles(articlesData);
      setKeywordStats(keywordsData);
      setCategoryStats(categoriesData);
      setNetworkData(network);
      setStats(statsData);
      setCollections(collectionsData);
    } catch (error) {
      console.error("데이터 로드 실패:", error);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => { loadAllData(); }, []);

  useEffect(() => {
    let tempArticles = articles
      .filter(a => filters.favoritesOnly ? a.is_favorite : true)
      .filter(a => filters.selectedSource === 'all' ? true : a.source === filters.selectedSource)
      .filter(a => filters.selectedCategory === 'all' ? true : a.main_category === filters.selectedCategory)
      .filter(a => filters.dateFrom ? new Date(a.published) >= new Date(filters.dateFrom) : true)
      .filter(a => filters.dateTo ? new Date(a.published) <= new Date(filters.dateTo) : true)
      .filter(a => {
        if (!filters.searchTerm) return true;
        const lower = filters.searchTerm.toLowerCase();
        return a.title.toLowerCase().includes(lower) || a.summary?.toLowerCase().includes(lower);
      });
    setFilteredArticles(tempArticles);
    setCurrentPage(1);
  }, [articles, filters]);

  const handleCollectNews = async () => {
    setCollecting(true);
    try {
      const result = await newsApi.collectNewsNow();
      alert(`뉴스 수집 완료: ${result.inserted || 0}개 신규`);
      await loadAllData(false);
    } catch (error) { alert("뉴스 수집에 실패했습니다."); }
    finally { setCollecting(false); }
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

  // [복원] 핸들러 함수들
  const handleExtractKeywords = (id: number) => alert(`ID ${id} 키워드 추출 기능은 백엔드 자동화로 대체되었습니다.`);
  const onTranslate = (id: number) => alert(`ID ${id} 번역 기능은 준비 중입니다.`);
  const handleCreateCollection = async () => {
    const name = prompt('새 컬렉션 이름을 입력하세요:');
    if (name) {
      await newsApi.createCollection(name, {});
      const collectionsData = await newsApi.getCollections();
      setCollections(collectionsData);
    }
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
          <Box sx={{ p: 2, overflowY: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box flexGrow={1}>
              <Typography variant="h6" gutterBottom>🔧 필터링</Typography>
              <Stack spacing={2}>
                <FormControl fullWidth size="small"><InputLabel>뉴스 출처</InputLabel><Select value={filters.selectedSource} label="뉴스 출처" onChange={e => setFilters(f => ({...f, selectedSource: e.target.value}))}><MenuItem value="all">전체</MenuItem>{sources.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}</Select></FormControl>
                <FormControl fullWidth size="small"><InputLabel>대분류</InputLabel><Select value={filters.selectedCategory} label="대분류" onChange={e => setFilters(f => ({...f, selectedCategory: e.target.value}))}><MenuItem value="all">전체</MenuItem>{categories.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}</Select></FormControl>
                <TextField fullWidth label="키워드 검색" size="small" value={filters.searchTerm} onChange={e => setFilters(f => ({...f, searchTerm: e.target.value}))} />
                <TextField fullWidth type="date" label="시작일" size="small" value={filters.dateFrom} onChange={e => setFilters(f => ({...f, dateFrom: e.target.value}))} InputLabelProps={{ shrink: true }}/>
                <TextField fullWidth type="date" label="종료일" size="small" value={filters.dateTo} onChange={e => setFilters(f => ({...f, dateTo: e.target.value}))} InputLabelProps={{ shrink: true }}/>
                <FormControlLabel control={<Switch checked={filters.favoritesOnly} onChange={e => setFilters(f => ({...f, favoritesOnly: e.target.checked}))}/>} label="즐겨찾기만 보기"/>
              </Stack>
            </Box>
            <Box>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>📊 데이터 관리</Typography>
              <Button variant="outlined" fullWidth onClick={handleCreateCollection} sx={{ mb: 1.5 }}>📁 새 컬렉션 만들기</Button>
              <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover' }}>
                <Typography variant="body2">총 {stats.total_articles || 0}개 기사</Typography>
                <Typography variant="body2">{stats.total_sources || 0}개 뉴스 소스</Typography>
                <Typography variant="body2">⭐ {stats.total_favorites || 0}개 즐겨찾기</Typography>
              </Paper>
            </Box>
          </Box>
        </Drawer>

        <Box component="main" sx={{ flexGrow: 1, p: 3, ml: drawerOpen ? '300px' : 0, transition: 'margin-left 0.3s' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tab icon={<ArticleIcon />} label="뉴스 목록" />
            <Tab icon={<Analytics />} label="분석" />
            <Tab icon={<Cloud />} label="워드클라우드" />
            <Tab icon={<Favorite />} label="즐겨찾기" />
            <Tab icon={<DarkMode />} label="테마" />
          </Tabs>

          {loading ? <CircularProgress sx={{ display: 'block', mx: 'auto', my: 4 }} /> :
            <>
              <TabPanel value={tabValue} index={0}>
                <Typography variant="h5" gutterBottom>📰 뉴스 목록 ({filteredArticles.length}건)</Typography>
                {paginatedArticles.length > 0 ? paginatedArticles.map(article => <ArticleCard key={article.id} article={article} onToggleFavorite={handleToggleFavorite} onExtractKeywords={handleExtractKeywords} onTranslate={onTranslate} />) : <Alert severity="info">표시할 뉴스가 없습니다.</Alert>}
                {Math.ceil(filteredArticles.length / itemsPerPage) > 1 && <Pagination count={Math.ceil(filteredArticles.length / itemsPerPage)} page={currentPage} onChange={(_, page) => setCurrentPage(page)} sx={{ mt: 2, display: 'flex', justifyContent: 'center' }} />}
              </TabPanel>
              <TabPanel value={tabValue} index={1}>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}><Paper sx={{ p: 2 }}><Typography variant="h6">🔥 인기 키워드</Typography><List dense>{keywordStats.slice(0, 15).map(s => <ListItem key={s.keyword}><ListItemText primary={s.keyword} secondary={`${s.count}회`} /></ListItem>)}</List></Paper></Grid>
                  <Grid item xs={12} md={6}><Paper sx={{ p: 2 }}><Typography variant="h6">📊 카테고리별 기사 수</Typography>{categoryStats.length > 0 ? <CategoryChart data={categoryStats} /> : <Alert severity="info">데이터 없음</Alert>}</Paper></Grid>
                  <Grid item xs={12}><KeywordNetwork data={networkData} /></Grid>
                </Grid>
              </TabPanel>
              <TabPanel value={tabValue} index={2}><Paper sx={{ p: 2, height: 600 }}><KeywordCloud keywords={keywordStats} /></Paper></TabPanel>
              <TabPanel value={tabValue} index={3}>
                {articles.filter(a => a.is_favorite).length > 0 ? articles.filter(a => a.is_favorite).map(article => <ArticleCard key={article.id} article={article} onToggleFavorite={handleToggleFavorite} onExtractKeywords={handleExtractKeywords} onTranslate={onTranslate} />) : <Alert severity="info">즐겨찾기한 뉴스가 없습니다.</Alert>}
              </TabPanel>
              <TabPanel value={tabValue} index={4}><ColorPalette /></TabPanel>
            </>
          }
        </Box>
      </Box>
    </ThemeProvider>
  );
}



