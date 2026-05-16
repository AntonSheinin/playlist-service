import type { ChangeEventHandler, HTMLInputTypeAttribute, KeyboardEventHandler } from "react";
import { TextField } from "@mui/material";

interface InputProps {
  id?: string;
  name?: string;
  type?: HTMLInputTypeAttribute;
  label?: string;
  error?: string;
  hint?: string;
  value?: string | number | readonly string[];
  defaultValue?: string | number | readonly string[];
  onChange?: ChangeEventHandler<HTMLInputElement>;
  placeholder?: string;
  autoComplete?: string;
  className?: string;
  autoFocus?: boolean;
  onKeyDown?: KeyboardEventHandler<HTMLInputElement>;
  readOnly?: boolean;
  disabled?: boolean;
  required?: boolean;
  min?: string | number;
  max?: string | number;
  step?: string | number;
}

export function Input({
  label,
  error,
  hint,
  id,
  readOnly,
  className,
  ...props
}: InputProps) {
  return (
    <TextField
      id={id}
      label={label}
      error={!!error}
      helperText={error || hint}
      fullWidth
      className={className}
      slotProps={readOnly ? { htmlInput: { readOnly: true } } : undefined}
      {...props}
    />
  );
}
