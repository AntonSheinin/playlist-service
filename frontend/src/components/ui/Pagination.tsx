import { Button } from "./Button";

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
    <div className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 md:flex-row md:items-center md:justify-between">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:space-x-4">
        <span className="text-sm text-slate-700">
          Page {page} of {pages} ({total} {label})
        </span>
        {onPerPageChange && perPage && (
          <select
            value={perPage}
            onChange={(e) => onPerPageChange(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            {perPageOptions.map((n) => (
              <option key={n} value={n}>
                {n} per page
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {onPerPageChange ? (
          // Full pagination: First/Previous/Next/Last
          <>
            <Button
              onClick={() => onPageChange(1)}
              disabled={page <= 1}
              size="sm"
              variant="secondary"
            >
              First
            </Button>
            <Button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              size="sm"
              variant="secondary"
            >
              Previous
            </Button>
            <Button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= pages}
              size="sm"
              variant="secondary"
            >
              Next
            </Button>
            <Button
              onClick={() => onPageChange(pages)}
              disabled={page >= pages}
              size="sm"
              variant="secondary"
            >
              Last
            </Button>
          </>
        ) : (
          // Simple pagination: Previous/Next only
          <>
            {page > 1 && (
              <Button
                onClick={() => onPageChange(page - 1)}
                size="sm"
                variant="secondary"
              >
                Previous
              </Button>
            )}
            {page < pages && (
              <Button
                onClick={() => onPageChange(page + 1)}
                size="sm"
                variant="secondary"
              >
                Next
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
