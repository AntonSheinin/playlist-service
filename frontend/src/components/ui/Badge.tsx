import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

const colorMap = {
  green: "status-success",
  red: "status-danger",
  blue: "status-info",
  yellow: "status-warning",
  gray: "status-neutral",
} as const;

interface BadgeProps {
  variant?: keyof typeof colorMap;
  className?: string;
  children: ReactNode;
  onClick?: () => void;
}

export function Badge({ variant = "gray", children, onClick, className }: BadgeProps) {
  const classes = cn(
    "inline-flex min-h-5 items-center rounded-full border px-2 py-0.5 text-xs font-semibold leading-none",
    onClick && "cursor-pointer transition hover:brightness-95",
    colorMap[variant],
    className
  );

  if (onClick) {
    return (
      <button type="button" className={classes} onClick={onClick}>
        {children}
      </button>
    );
  }

  return <span className={classes}>{children}</span>;
}
