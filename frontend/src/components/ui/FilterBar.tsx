import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

interface FilterBarProps {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function FilterBar({ children, className, contentClassName }: FilterBarProps) {
  return (
    <div className={cn("rounded-lg border border-border bg-card p-4 shadow-sm", className)}>
      <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-4", contentClassName)}>
        {children}
      </div>
    </div>
  );
}
