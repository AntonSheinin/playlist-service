import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Button as MuiButton, CircularProgress } from "@mui/material";

const variantMap = {
  primary: { color: "primary", variant: "contained" },
  danger: { color: "error", variant: "contained" },
  secondary: { color: "inherit", variant: "outlined" },
  ghost: { color: "inherit", variant: "text" },
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
  ...props
}: ButtonProps) {
  const muiVariant = variantMap[variant];

  return (
    <MuiButton
      color={muiVariant.color}
      variant={muiVariant.variant}
      size={size === "sm" ? "small" : "medium"}
      disabled={disabled || loading}
      startIcon={loading ? <CircularProgress size={14} color="inherit" /> : undefined}
      {...props}
    >
      {children}
    </MuiButton>
  );
}
