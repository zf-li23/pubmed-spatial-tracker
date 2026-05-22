import { useState, useEffect, useMemo, useCallback } from 'react';
import { Article, FilterState } from './types';
import { loadArticles, filterArticles, extractFilterOptions, emptyFilter } from './utils';
import SearchBar from './components/SearchBar';
import FilterPanel from './components/FilterPanel';
import DataTable from './components/DataTable';
import ArticleDetail from './components/ArticleDetail';

export default function App() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(emptyFilter);
  const [page, setPage] = useState(1);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  // 加载数据
  useEffect(() => {
    loadArticles()
      .then(data => {
        setArticles(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // 提取筛选选项（数据加载后）
  const filterOptions = useMemo(() => {
    if (articles.length === 0) return { years: [], categories: [], tags: [], technologies: [], biologicalTopics: [], journals: [] };
    return extractFilterOptions(articles);
  }, [articles]);

  // 筛选后的文章
  const filtered = useMemo(() => filterArticles(articles, filters), [articles, filters]);

  // 筛选变更时重置页码
  useEffect(() => { setPage(1); }, [filters]);

  // 切换筛选器值（仅 Set 类型字段）
  const handleToggle = useCallback((key: keyof FilterState, value: string) => {
    setFilters(prev => {
      const set = prev[key] as Set<string>;
      const nextSet = new Set(set);
      if (nextSet.has(value)) {
        nextSet.delete(value);
      } else {
        nextSet.add(value);
      }
      return { ...prev, [key]: nextSet };
    });
  }, []);

  // 搜索框
  const handleSearch = useCallback((v: string) => {
    setFilters(prev => ({ ...prev, search: v }));
  }, []);

  // 清除全部筛选
  const handleClearAll = useCallback(() => {
    setFilters(emptyFilter());
  }, []);

  // 统计
  const stats = useMemo(() => {
    const total = articles.length;
    const withData = articles.filter(a => a.has_new_data).length;
    const withCode = articles.filter(a => a.has_code).length;
    return { total, withData, withCode };
  }, [articles]);

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading {stats.total > 0 ? stats.total.toLocaleString() : ''} articles…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-error">
        <h2>Failed to load data</h2>
        <p>{error}</p>
        <p className="error-hint">Make sure you have run <code>python3 scripts/convert_csv.py</code> to generate <code>public/data/articles.json</code>.</p>
      </div>
    );
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <h1>PubMed Spatial Tracker</h1>
          <p className="header-subtitle">
            LLM-annotated spatial transcriptomics literature database
          </p>
        </div>
        <div className="header-stats">
          <div className="stat">
            <span className="stat-num">{stats.total.toLocaleString()}</span>
            <span className="stat-label">Articles</span>
          </div>
          <div className="stat">
            <span className="stat-num">{stats.withData.toLocaleString()}</span>
            <span className="stat-label">With Data</span>
          </div>
          <div className="stat">
            <span className="stat-num">{stats.withCode.toLocaleString()}</span>
            <span className="stat-label">With Code</span>
          </div>
        </div>
      </header>

      {/* 详情页 */}
      {selectedArticle ? (
        <div className="main-area">
          <main className="content">
            <ArticleDetail
              article={selectedArticle}
              onBack={() => setSelectedArticle(null)}
            />
          </main>
        </div>
      ) : (
        <>
          {/* 搜索栏 */}
          <div className="search-row">
            <SearchBar value={filters.search} onChange={handleSearch} />
            <span className="result-count">
              {filtered.length.toLocaleString()} results
              {filters.search && ` for "${filters.search}"`}
            </span>
          </div>

          {/* 主区域 */}
          <div className="main-area">
            <FilterPanel
              options={filterOptions}
              filters={filters}
              onToggle={handleToggle}
              onClearAll={handleClearAll}
            />
            <main className="content">
              <DataTable
                articles={filtered}
                page={page}
                onPageChange={setPage}
                onArticleClick={setSelectedArticle}
              />
            </main>
          </div>
        </>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <p>
          PubMed Spatial Tracker · LLM annotations by DeepSeek ·{' '}
          <a href="https://pubmed.ncbi.nlm.nih.gov/" target="_blank" rel="noopener noreferrer">PubMed</a>
        </p>
      </footer>
    </div>
  );
}
