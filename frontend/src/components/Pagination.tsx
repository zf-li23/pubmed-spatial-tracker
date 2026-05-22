interface PaginationProps {
  page: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
  onPage: (p: number) => void;
}

export default function Pagination({ page, totalPages, onPrev, onNext, onPage }: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages: number[] = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="pagination">
      <button onClick={onPrev} disabled={page === 1}>← Prev</button>
      {start > 1 && <>
        <button onClick={() => onPage(1)}>1</button>
        {start > 2 && <span className="pagination-ellipsis">…</span>}
      </>}
      {pages.map(p => (
        <button
          key={p}
          onClick={() => onPage(p)}
          className={p === page ? 'active' : ''}
        >
          {p}
        </button>
      ))}
      {end < totalPages && <>
        {end < totalPages - 1 && <span className="pagination-ellipsis">…</span>}
        <button onClick={() => onPage(totalPages)}>{totalPages}</button>
      </>}
      <button onClick={onNext} disabled={page === totalPages}>Next →</button>
    </div>
  );
}
