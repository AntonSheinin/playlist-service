import { Children, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, SlidersHorizontal } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";
import { Select } from "./Select";

export interface MobileSortOption {
  value: string;
  label: string;
}

interface MobileRecordListProps {
  children: ReactNode;
  empty?: ReactNode;
  className?: string;
}

export function MobileRecordList({ children, empty, className }: MobileRecordListProps) {
  const hasChildren = Children.count(children) > 0;

  return (
    <div className={cn("divide-y divide-border rounded-lg border border-border bg-card sm:hidden", className)}>
      {hasChildren ? children : empty}
    </div>
  );
}

interface MobileRecordItemProps {
  children: ReactNode;
  muted?: boolean;
  edited?: boolean;
  className?: string;
}

export function MobileRecordItem({ children, muted, edited, className }: MobileRecordItemProps) {
  return (
    <article
      className={cn(
        "space-y-3 px-4 py-4",
        muted && "bg-muted text-muted-foreground",
        edited && "bg-[var(--color-table-edited)]",
        className
      )}
    >
      {children}
    </article>
  );
}

interface MobileFieldProps {
  label: string;
  children: ReactNode;
  className?: string;
}

export function MobileField({ label, children, className }: MobileFieldProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <div className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">{label}</div>
      <div className="mt-1 min-w-0 text-sm text-foreground">{children}</div>
    </div>
  );
}

export function MobileCardActions({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-wrap justify-end gap-2 pt-1", className)}>{children}</div>;
}

interface MobileSortSelectProps {
  value: string;
  direction: string;
  options: MobileSortOption[];
  onSort: (field: string) => void;
  className?: string;
}

export function MobileSortSelect({ value, direction, options, onSort, className }: MobileSortSelectProps) {
  return (
    <div className={cn("grid grid-cols-[1fr_auto] items-end gap-2 sm:hidden", className)}>
      <Select label="Sort by" value={value} onChange={(event) => onSort(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
      <Button
        type="button"
        variant="secondary"
        className="min-h-10 w-11 px-0"
        onClick={() => onSort(value)}
        aria-label={`Sort ${direction === "asc" ? "descending" : "ascending"}`}
        title={`Sort ${direction === "asc" ? "descending" : "ascending"}`}
      >
        {direction === "asc" ? <ArrowUp className="h-4 w-4" aria-hidden="true" /> : <ArrowDown className="h-4 w-4" aria-hidden="true" />}
      </Button>
    </div>
  );
}

interface MobileFilterToggleProps {
  activeCount: number;
  children: ReactNode;
}

export function MobileFilterToggle({ activeCount, children }: MobileFilterToggleProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-3 sm:hidden">
      <Button
        type="button"
        variant="secondary"
        className="min-h-11 w-full justify-between"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        <span className="inline-flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
          Filters
        </span>
        {activeCount > 0 && (
          <span className="status-info rounded-full border px-2 py-0.5 text-xs font-semibold">
            {activeCount}
          </span>
        )}
      </Button>
      {open && <div className="grid grid-cols-1 gap-4">{children}</div>}
    </div>
  );
}
