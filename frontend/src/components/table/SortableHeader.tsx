import { TableSortLabel } from "@mui/material";

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
    <TableSortLabel
      active={active}
      direction={active && sortDir === "desc" ? "desc" : "asc"}
      onClick={() => onSort(field)}
    >
      {label}
    </TableSortLabel>
  );
}
