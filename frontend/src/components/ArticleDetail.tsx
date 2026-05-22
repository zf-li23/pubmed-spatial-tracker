import { Article, CONFIDENCE_MAP, CATEGORY_COLORS } from '../types';

interface ArticleDetailProps {
  article: Article;
  onBack: () => void;
}

export default function ArticleDetail({ article, onBack }: ArticleDetailProps) {
  const c = CONFIDENCE_MAP[article.confidence] ?? CONFIDENCE_MAP.medium;
  const catColor = CATEGORY_COLORS[article.category] || '#666';

  return (
    <div className="detail-page">
      {/* 顶栏 */}
      <div className="detail-topbar">
        <button className="back-btn" onClick={onBack}>← Back to results</button>
        <div className="detail-topbar-links">
          <a
            href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`}
            target="_blank"
            rel="noopener noreferrer"
            className="pubmed-btn"
          >
            View on PubMed ↗
          </a>
        </div>
      </div>

      {/* 标题 */}
      <h2 className="detail-title">{article.title}</h2>

      {/* 元信息行 */}
      <div className="detail-meta">
        <span className="detail-meta-item">
          <strong>PMID:</strong>{' '}
          <a href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`} target="_blank" rel="noopener noreferrer">
            {article.pmid}
          </a>
        </span>
        {article.doi && (
          <span className="detail-meta-item">
            <strong>DOI:</strong>{' '}
            <a href={`https://doi.org/${article.doi}`} target="_blank" rel="noopener noreferrer">
              {article.doi}
            </a>
          </span>
        )}
        <span className="detail-meta-item"><strong>Year:</strong> {article.pub_year}</span>
        <span className="detail-meta-item"><strong>Journal:</strong> <em>{article.journal}</em></span>
      </div>

      {/* LLM 标注摘要 */}
      <div className="detail-annotations">
        <div className="detail-anno-row">
          <span className="detail-anno-label">Category:</span>
          <span className="cat-tag" style={{ background: catColor }}>{article.category || '—'}</span>
        </div>

        <div className="detail-anno-row">
          <span className="detail-anno-label">Tags:</span>
          <span className="detail-anno-values">
            {article.tags.length > 0
              ? article.tags.map(t => <span key={t} className="tag-chip">{t}</span>)
              : '—'}
          </span>
        </div>

        <div className="detail-anno-row">
          <span className="detail-anno-label">Technology:</span>
          <span className="detail-anno-values">
            {article.technology.length > 0
              ? article.technology.map(t => <span key={t} className="tech-chip">{t}</span>)
              : '—'}
          </span>
        </div>

        <div className="detail-anno-row">
          <span className="detail-anno-label">Biological Topic:</span>
          <span>{article.biological_topic || '—'}</span>
        </div>

        <div className="detail-anno-row">
          <span className="detail-anno-label">Indicators:</span>
          <span className="detail-indicators">
            {article.has_new_data && <span className="badge badge-data">📊 New Data</span>}
            {article.has_code && <span className="badge badge-code">💻 New Code</span>}
            <span className="badge badge-conf" style={{ color: c.color, background: c.bg }}>
              Confidence: {c.label}
            </span>
          </span>
        </div>
      </div>

      {/* 摘要 */}
      {article.abstract && (
        <section className="detail-section">
          <h3 className="detail-section-title">Abstract</h3>
          <p className="detail-abstract">{article.abstract}</p>
        </section>
      )}

      {/* MeSH Terms */}
      {article.mesh_terms.length > 0 && (
        <section className="detail-section">
          <h3 className="detail-section-title">MeSH Terms</h3>
          <div className="detail-chips">
            {article.mesh_terms.map(m => (
              <span key={m} className="mesh-chip">{m}</span>
            ))}
          </div>
        </section>
      )}

      {/* Keywords */}
      {article.keywords.length > 0 && (
        <section className="detail-section">
          <h3 className="detail-section-title">Keywords</h3>
          <div className="detail-chips">
            {article.keywords.map(k => (
              <span key={k} className="keyword-chip">{k}</span>
            ))}
          </div>
        </section>
      )}

      {/* 底部 PubMed 按钮 */}
      <div className="detail-footer">
        <a
          href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="pubmed-btn"
        >
          Open in PubMed ↗
        </a>
      </div>
    </div>
  );
}
