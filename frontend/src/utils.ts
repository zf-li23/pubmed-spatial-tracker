import { Article, FilterState } from './types';

/** 从 public/data/articles.json 加载数据 */
export async function loadArticles(): Promise<Article[]> {
  const resp = await fetch('./data/articles.json');
  if (!resp.ok) throw new Error(`Failed to load articles: ${resp.status}`);
  return resp.json();
}

/** 根据筛选条件过滤文章 */
export function filterArticles(articles: Article[], f: FilterState): Article[] {
  return articles.filter(a => {
    // 搜索框：匹配 pmid / title / doi（大小写不敏感）
    if (f.search) {
      const q = f.search.toLowerCase();
      const matchSearch =
        a.pmid.includes(q) ||
        a.title.toLowerCase().includes(q) ||
        a.doi.toLowerCase().includes(q);
      if (!matchSearch) return false;
    }

    // 年份
    if (f.years.size > 0 && !f.years.has(a.pub_year)) return false;

    // 分类
    if (f.categories.size > 0 && !f.categories.has(a.category)) return false;

    // 标签（文章 tags 数组中任一命中）
    if (f.tags.size > 0 && !a.tags.some(t => f.tags.has(t))) return false;

    // 技术（文章 technology 数组中任一命中）
    if (f.technologies.size > 0 && !a.technology.some(t => f.technologies.has(t))) return false;

    // 生物主题
    if (f.biologicalTopics.size > 0 && !f.biologicalTopics.has(a.biological_topic)) return false;

    // 期刊
    if (f.journals.size > 0 && !f.journals.has(a.journal)) return false;

    return true;
  });
}

/** 从文章列表中提取所有可选值 */
export function extractFilterOptions(articles: Article[]) {
  const years = [...new Set(articles.map(a => a.pub_year))].sort((a, b) => +b - +a);
  const categories = [...new Set(articles.map(a => a.category))].filter(Boolean).sort();
  const tags = [...new Set(articles.flatMap(a => a.tags))].filter(Boolean).sort();
  const technologies = [...new Set(articles.flatMap(a => a.technology))].filter(Boolean).sort();
  const biologicalTopics = [...new Set(articles.map(a => a.biological_topic))].filter(Boolean).sort();
  const journals = [...new Set(articles.map(a => a.journal))].filter(Boolean).sort();

  return { years, categories, tags, technologies, biologicalTopics, journals };
}

/** 构建空筛选状态 */
export function emptyFilter(): FilterState {
  return {
    search: '',
    years: new Set(),
    categories: new Set(),
    tags: new Set(),
    technologies: new Set(),
    biologicalTopics: new Set(),
    journals: new Set(),
  };
}
