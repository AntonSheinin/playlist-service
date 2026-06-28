import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { cn } from "../../lib/utils";

interface SortableHeaderProps {
  label: string;
  field: string;
  sortBy: string;
  sortDir: string;
  onSort: (field: string) => void;
  className?: string;
}

export function SortableHeader({ label, field, sortBy, sortDir, onSort }: SortableHeaderProps) {
  const active = sortBy === field;

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground hover:text-foreground",
        active && "text-foreground"
      )}
      onClick={() => onSort(field)}
      aria-sort={active ? (sortDir === "desc" ? "descending" : "ascending") : "none"}
    >
      {label}
      {active ? (
        sortDir === "desc" ? <ArrowDown className="h-3.5 w-3.5" /> : <ArrowUp className="h-3.5 w-3.5" />
      ) : (
        <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
      )}
    </button>
  );
}
