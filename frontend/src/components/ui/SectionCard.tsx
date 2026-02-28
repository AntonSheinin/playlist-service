import type { ReactNode } from "react";
import { Card } from "./Card";
import { cn } from "../../utils/cn";

interface SectionCardProps {
  title: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function SectionCard({
  title,
  children,
  actions,
  className,
  bodyClassName,
}: SectionCardProps) {
  const titleNode =
    typeof title === "string"
      ? <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      : <div className="text-lg font-semibold text-slate-900">{title}</div>;

  return (
    <Card className={className}>
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
        {titleNode}
        {actions}
      </div>
      <div className={cn("px-6 py-4", bodyClassName)}>{children}</div>
    </Card>
  );
}
