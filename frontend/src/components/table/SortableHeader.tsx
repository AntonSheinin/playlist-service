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
        "flex items-center gap-1 text-left w-full hover:text-gray-700",
        className
      )}
    >
      <span>{label}</span>
      <span className="text-gray-400">
        {active ? (sortDir === "asc" ? "▲" : "▼") : ""}
      </span>
    </button>
  );
}
