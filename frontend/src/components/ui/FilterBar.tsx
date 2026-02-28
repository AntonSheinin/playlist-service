import type { ReactNode } from "react";
import { Card } from "./Card";
import { cn } from "../../utils/cn";

interface FilterBarProps {
  children: ReactNode;
  className?: string;
}

export function FilterBar({ children, className }: FilterBarProps) {
  return (
    <Card className={cn("p-4", className)}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">{children}</div>
    </Card>
  );
}
