import type { ChangeEventHandler, ReactNode } from "react";
import { TextField } from "@mui/material";

interface SelectProps {
  id?: string;
  name?: string;
  label?: string;
  value?: string | number | readonly string[];
  defaultValue?: string | number | readonly string[];
  onChange?: ChangeEventHandler<HTMLInputElement>;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  children: ReactNode;
}

export function Select({ label, id, children, className, ...props }: SelectProps) {
  return (
    <TextField
      id={id}
      label={label}
      select
      fullWidth
      className={className}
      slotProps={{ select: { native: true } }}
      {...props}
    >
      {children}
    </TextField>
  );
}
