import type { HTMLAttributes, ReactNode } from "react";
import { Card as MuiCard } from "@mui/material";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ children, ...props }: CardProps) {
  return (
    <MuiCard {...props} sx={{ overflow: "hidden", ...(props.style as object) }}>
      {children}
    </MuiCard>
  );
}
