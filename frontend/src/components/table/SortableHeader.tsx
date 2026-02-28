import { cn } from "../../utils/cn";

interface SortableHeaderProps {
  label: string;
  field: string;
  sortBy: string;
  sortDir: string;
  onSort: (field: string) => void;
  className?: string;
}

export function SortableHeader({
  label,
  field,
  sortBy,
  sortDir,
  onSort,
  className,
}: SortableHeaderProps) {
  const active = sortBy === field;

  return (
    <button
      type="button"
      onClick={() => onSort(field)}
      className={cn(
        "flex w-full items-center gap-1 text-left hover:text-slate-700",
        className
      )}
    >
      <span>{label}</span>
      <span className="text-slate-400" aria-hidden="true">
        {active ? (sortDir === "asc" ? "^" : "v") : ""}
      </span>
    </button>
  );
}
