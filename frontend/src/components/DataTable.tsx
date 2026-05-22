import { Article } from '../types';
import { CATEGORY_COLORS, CONFIDENCE_MAP } from '../types';

const PAGE_SIZE = 50;

interface DataTableProps {
  articles: Article[];
  page: number;
  onPageChange: (p: number) => void;
  onArticleClick: (article: Article) => void;
}

/** 紧凑型浏览器表格：标题可点击进入详情，PMID/DOI/期刊移到详情页 */
export default function DataTable({ articles, page, onPageChange, onArticleClick }: DataTableProps) {
  const totalPages = Math.ceil(articles.length / PAGE_SIZE);
  const safePage = Math.min(page, Math.max(1, totalPages));
  const start = (safePage - 1) * PAGE_SIZE;
  const displayed = articles.slice(start, start + PAGE_SIZE);

  if (articles.length === 0) {
    return (
      <div className="empty-state">
        <p>No articles match the current filters.</p>
        <p className="empty-hint">Try adjusting your search or filter criteria.</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <div className="table-info">
        Showing {start + 1}–{Math.min(start + PAGE_SIZE, articles.length)} of {articles.length.toLocaleString()} articles
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th className="col-title">Title</th>
              <th className="col-year">Year</th>
              <th className="col-cat">Category</th>
              <th className="col-tags">Tags</th>
              <th className="col-tech">Technology</th>
              <th className="col-topic">Bio Topic</th>
              <th className="col-badges">Indicators</th>
            </tr>
          </thead>
          <tbody>
            {displayed.map(a => (
              <tr key={a.pmid}>
                <td className="col-title">
                  <a
                    className="title-link"
                    onClick={(e) => { e.preventDefault(); onArticleClick(a); }}
                    href="#"
                    title={a.title}
                  >
                    {a.title}
                  </a>
                </td>
                <td className="col-year">{a.pub_year}</td>
                <td className="col-cat">
                  {a.category && (
                    <span
                      className="cat-tag"
                      style={{ background: CATEGORY_COLORS[a.category] || '#666' }}
                    >
                      {a.category}
                    </span>
                  )}
                </td>
                <td className="col-tags">
                  {a.tags.length > 0
                    ? a.tags.map(t => <span key={t} className="tag-chip">{t}</span>)
                    : <span className="text-muted">—</span>}
                </td>
                <td className="col-tech">
                  {a.technology.length > 0
                    ? a.technology.map(t => <span key={t} className="tech-chip">{t}</span>)
                    : <span className="text-muted">—</span>}
                </td>
                <td className="col-topic">
                  {a.biological_topic || <span className="text-muted">—</span>}
                </td>
                <td className="col-badges">
                  <CompactBadges article={a} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 底部分页 */}
      <div className="table-footer">
        <div className="table-info">
          Page {safePage} of {totalPages}
        </div>
        <div className="pagination">
          <button onClick={() => onPageChange(1)} disabled={safePage === 1}>««</button>
          <button onClick={() => onPageChange(safePage - 1)} disabled={safePage === 1}>←</button>
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            let pageNum: number;
            if (totalPages <= 7) {
              pageNum = i + 1;
            } else if (safePage <= 4) {
              pageNum = i + 1;
            } else if (safePage >= totalPages - 3) {
              pageNum = totalPages - 6 + i;
            } else {
              pageNum = safePage - 3 + i;
            }
            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={pageNum === safePage ? 'active' : ''}
              >
                {pageNum}
              </button>
            );
          })}
          <button onClick={() => onPageChange(safePage + 1)} disabled={safePage >= totalPages}>→</button>
          <button onClick={() => onPageChange(totalPages)} disabled={safePage >= totalPages}>»»</button>
        </div>
      </div>
    </div>
  );
}

/** 紧凑徽章：只显示图标，悬停看详情 */
function CompactBadges({ article }: { article: Article }) {
  const c = CONFIDENCE_MAP[article.confidence] ?? CONFIDENCE_MAP.medium;

  return (
    <span className="badge-row">
      {article.has_new_data && (
        <span className="badge badge-data" title="Has New Data (collected new experimental data)">📊</span>
      )}
      {article.has_code && (
        <span className="badge badge-code" title="Has New Code (new analysis method or tool)">💻</span>
      )}
      <span
        className="badge badge-conf"
        style={{ color: c.color, background: c.bg }}
        title={`LLM confidence: ${c.label}`}
      >
        {c.label[0].toUpperCase()}
      </span>
    </span>
  );
}
