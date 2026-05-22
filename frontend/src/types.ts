/** 一篇文章的完整数据（annotated + articles 合并） */
export interface Article {
  pmid: string;
  title: string;
  doi: string;
  abstract: string;
  pub_year: string;
  journal: string;
  mesh_terms: string[];
  keywords: string[];
  // LLM 标注字段
  category: string;
  tags: string[];
  technology: string[];
  biological_topic: string;
  has_new_data: boolean;
  has_code: boolean;
  confidence: 'high' | 'medium' | 'low';
}

/** 筛选状态 */
export interface FilterState {
  search: string;
  years: Set<string>;
  categories: Set<string>;
  tags: Set<string>;
  technologies: Set<string>;
  biologicalTopics: Set<string>;
  journals: Set<string>;
}

/** 筛选器可选值 */
export interface FilterOptions {
  years: string[];
  categories: string[];
  tags: string[];
  technologies: string[];
  biologicalTopics: string[];
  journals: string[];
}

/** 置信度对应的颜色与标签 */
export const CONFIDENCE_MAP: Record<string, { label: string; color: string; bg: string }> = {
  high:   { label: 'High',   color: '#1a7a1a', bg: '#d4edda' },
  medium: { label: 'Medium', color: '#8b6d00', bg: '#fff3cd' },
  low:    { label: 'Low',    color: '#8b1a1a', bg: '#f8d7da' },
};

/** 分类对应的颜色 */
export const CATEGORY_COLORS: Record<string, string> = {
  Research:      '#2563eb',
  Technology:    '#7c3aed',
  Review:        '#059669',
  Protocol:      '#d97706',
  'Data Resource': '#dc2626',
  Benchmark:     '#0891b2',
};
