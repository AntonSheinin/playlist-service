import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Card } from "./Card";

interface SectionCardProps {
  title: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function SectionCard({ title, children, actions, className, bodyClassName }: SectionCardProps) {
  return (
    <Card className={className}>
      <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
        {typeof title === "string" ? (
          <h2 className="text-lg font-semibold text-card-foreground">{title}</h2>
        ) : (
          title
        )}
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </Card>
  );
}
