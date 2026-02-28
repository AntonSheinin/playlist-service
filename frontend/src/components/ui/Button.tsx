import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "../../utils/cn";

const variants = {
  primary:
    "bg-sky-600 text-white hover:bg-sky-700 focus:ring-sky-200 border border-sky-600",
  danger:
    "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-200 border border-rose-600",
  secondary:
    "bg-white text-slate-800 hover:bg-slate-50 focus:ring-slate-200 border border-slate-300",
  ghost:
    "text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:ring-slate-200 border border-transparent",
};

const sizes = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading,
  className,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed",
        "transition-colors",
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
}
