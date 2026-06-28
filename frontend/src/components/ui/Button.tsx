import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

const variantMap = {
  primary: "bg-primary text-primary-foreground shadow-sm hover:brightness-95",
  danger: "bg-destructive text-destructive-foreground shadow-sm hover:brightness-95",
  secondary: "border border-border bg-card text-card-foreground shadow-sm hover:bg-muted",
  ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
  outlined: "border border-border bg-card text-card-foreground shadow-sm hover:bg-muted",
} as const;

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "color"> {
  variant?: keyof typeof variantMap;
  size?: "sm" | "md";
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading,
  disabled,
  children,
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition disabled:cursor-not-allowed disabled:opacity-60",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        size === "sm" ? "min-h-8 px-3 py-1 text-sm" : "min-h-9 px-4 py-2 text-sm",
        variantMap[variant],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
