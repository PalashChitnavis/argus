// Simple prev/next pagination control for tables backed by limit/offset
// APIs. Purely presentational — the parent owns `offset` state and passes
// it back in via onPageChange.
//
// Renders nothing when there's only one page (total <= limit), so it's
// safe to drop into any section unconditionally.
export default function Pagination({ total, limit, offset, onPageChange }) {
  if (total <= limit) return null;

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="pagination">
      <button
        className="btn btn-sm btn-ghost"
        disabled={offset === 0}
        onClick={() => onPageChange(Math.max(0, offset - limit))}
      >
        ‹ Prev
      </button>
      <span className="pagination-status text-dim">
        Page {currentPage} of {totalPages} · {total} total
      </span>
      <button
        className="btn btn-sm btn-ghost"
        disabled={offset + limit >= total}
        onClick={() => onPageChange(offset + limit)}
      >
        Next ›
      </button>
    </div>
  );
}