import { Chip } from "@mui/material";

const colorMap = {
  green: "success",
  red: "error",
  blue: "primary",
  yellow: "warning",
  gray: "default",
} as const;

interface BadgeProps {
  variant?: keyof typeof colorMap;
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
}

export function Badge({ variant = "gray", children, onClick }: BadgeProps) {
  return (
    <Chip
      component={onClick ? "button" : "span"}
      clickable={!!onClick}
      onClick={onClick}
      color={colorMap[variant]}
      variant={variant === "gray" ? "outlined" : "filled"}
      label={children}
      size="small"
    />
  );
}
