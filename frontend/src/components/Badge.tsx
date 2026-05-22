import { Article } from '../types';
import { CONFIDENCE_MAP } from '../types';

interface BadgeProps {
  article: Article;
}

/** 行内小徽章：新数据 / 新代码 / 置信度 */
export default function Badge({ article }: BadgeProps) {
  const conf = CONFIDENCE_MAP[article.confidence] ?? CONFIDENCE_MAP.medium;

  return (
    <span className="badge-row">
      {article.has_new_data && (
        <span className="badge badge-data" title="Has New Data (collected new experimental data)">
          📊 Data
        </span>
      )}
      {article.has_code && (
        <span className="badge badge-code" title="Has New Code (new analysis method or tool)">
          💻 Code
        </span>
      )}
      <span
        className="badge badge-conf"
        style={{ color: conf.color, background: conf.bg }}
        title={`LLM annotation confidence: ${conf.label}`}
      >
        {conf.label}
      </span>
    </span>
  );
}
