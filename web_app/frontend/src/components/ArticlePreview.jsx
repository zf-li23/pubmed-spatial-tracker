export default function ArticlePreview({ row }) {
  if (!row) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 border-dashed border-2 border-gray-200 m-4 rounded">
        <span className="font-semibold text-lg italic tracking-wide">请在左侧表格单击行，浏览文献详情</span>
      </div>
    );
  }

  const shownCategory = row.category || row.auto_predicted_category || row.naive_category || "";
  const shownTags = row.tags || row.auto_predicted_tags || row.naive_tags || "";

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="text-xs text-gray-500 mb-1 flex justify-between">
          <span>{row.journal} • {row.pub_year}</span>
          {row.doi && (
            <a
              href={`https://doi.org/${row.doi}`}
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 underline font-bold"
            >
              DOI 链接
            </a>
          )}
        </div>
        <h2 className="text-lg font-bold text-gray-900 leading-snug">{row.title}</h2>
      </div>

      <div>
        <h3 className="font-semibold text-gray-700 mb-1 border-b pb-1">摘要 (Abstract)</h3>
        <div className="text-xs text-gray-600 h-[28vh] overflow-y-auto bg-gray-50 border p-3 rounded leading-relaxed shadow-inner">
          {row.abstract || "无可用摘要。"}
        </div>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-3">
        <div>
          <div className="text-xs font-bold text-gray-500 mb-1">PMID</div>
          <div className="text-sm text-gray-800">{row.pmid}</div>
        </div>
        <div>
          <div className="text-xs font-bold text-gray-500 mb-1">Category</div>
          <div className="text-sm text-gray-800">{shownCategory || "-"}</div>
        </div>
        <div>
          <div className="text-xs font-bold text-gray-500 mb-1">Tags</div>
          <div className="text-sm text-gray-800 break-words">{shownTags || "-"}</div>
        </div>
        <div>
          <div className="text-xs font-bold text-gray-500 mb-1">URL</div>
          {row.url ? (
            <a className="text-sm text-teal-700 underline break-all" href={row.url} target="_blank" rel="noreferrer">
              {row.url}
            </a>
          ) : (
            <div className="text-sm text-gray-500">-</div>
          )}
        </div>
      </div>

      <div className="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded p-3">
        当前为 GitHub Pages 静态只读模式：标注、上传、训练等后端功能已禁用。
      </div>
    </div>
  );
}
