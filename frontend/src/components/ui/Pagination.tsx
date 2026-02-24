interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
  perPage?: number;
  onPerPageChange?: (perPage: number) => void;
  label?: string;
}

const perPageOptions = [10, 20, 50, 100];

export function Pagination({
  page,
  pages,
  total,
  onPageChange,
  perPage,
  onPerPageChange,
  label = "items",
}: PaginationProps) {
  if (pages <= 1 && !onPerPageChange) return null;

  return (
    <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <span className="text-sm text-gray-700">
          Page {page} of {pages} ({total} {label})
        </span>
        {onPerPageChange && perPage && (
          <select
            value={perPage}
            onChange={(e) => onPerPageChange(Number(e.target.value))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            {perPageOptions.map((n) => (
              <option key={n} value={n}>
                {n} per page
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex space-x-2">
        {onPerPageChange ? (
          // Full pagination: First/Previous/Next/Last
          <>
            <button
              onClick={() => onPageChange(1)}
              disabled={page <= 1}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              First
            </button>
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= pages}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
            <button
              onClick={() => onPageChange(pages)}
              disabled={page >= pages}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Last
            </button>
          </>
        ) : (
          // Simple pagination: Previous/Next only
          <>
            {page > 1 && (
              <button
                onClick={() => onPageChange(page - 1)}
                className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
              >
                Previous
              </button>
            )}
            {page < pages && (
              <button
                onClick={() => onPageChange(page + 1)}
                className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
              >
                Next
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
