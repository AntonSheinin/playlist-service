import { cn } from "../../utils/cn";

const variants = {
  green: "bg-green-100 text-green-800",
  red: "bg-red-100 text-red-800",
  blue: "bg-blue-100 text-blue-800",
  yellow: "bg-yellow-100 text-yellow-800",
  gray: "bg-gray-100 text-gray-800",
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
        onClick && "cursor-pointer hover:opacity-80",
        className
      )}
    >
      {children}
    </Tag>
  );
}
