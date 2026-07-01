import { Button } from "./Button";
import { Select } from "./Select";

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
    <div className="border-t border-border px-4 py-3">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <p className="text-sm text-muted-foreground">
            Page {page} of {pages} ({total} {label})
          </p>
          {onPerPageChange && perPage && (
            <Select
              aria-label="Items per page"
              value={perPage}
              onChange={(e) => onPerPageChange(Number(e.target.value))}
              className="w-full sm:w-36"
            >
              {perPageOptions.map((n) => (
                <option key={n} value={n}>
                  {n} per page
                </option>
              ))}
            </Select>
          )}
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
          {onPerPageChange && (
            <Button variant="outlined" className="min-h-11 sm:min-h-9" onClick={() => onPageChange(1)} disabled={page <= 1}>
              First
            </Button>
          )}
          <Button variant="outlined" className="min-h-11 sm:min-h-9" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
            Previous
          </Button>
          <Button variant="outlined" className="min-h-11 sm:min-h-9" onClick={() => onPageChange(page + 1)} disabled={page >= pages}>
            Next
          </Button>
          {onPerPageChange && (
            <Button variant="outlined" className="min-h-11 sm:min-h-9" onClick={() => onPageChange(pages)} disabled={page >= pages}>
              Last
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
