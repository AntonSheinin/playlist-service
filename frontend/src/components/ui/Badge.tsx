import { cn } from "../../utils/cn";

const variants = {
  green: "bg-emerald-100 text-emerald-800",
  red: "bg-rose-100 text-rose-800",
  blue: "bg-sky-100 text-sky-800",
  yellow: "bg-amber-100 text-amber-800",
  gray: "bg-slate-100 text-slate-800",
};

interface BadgeProps {
  variant?: keyof typeof variants;
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
}

export function Badge({ variant = "gray", className, children, onClick }: BadgeProps) {
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      onClick={onClick}
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        variants[variant],
        onClick &&
          "cursor-pointer hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-sky-200",
        className
      )}
    >
      {children}
    </Tag>
  );
}
