import type { ChangeEventHandler, HTMLInputTypeAttribute, KeyboardEventHandler } from "react";
import { cn } from "../../lib/utils";

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
  required,
  ...props
}: InputProps) {
  const inputId = id || props.name;

  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-xs font-semibold uppercase tracking-normal text-muted-foreground">
          {label}
          {required && <span className="text-destructive"> *</span>}
        </span>
      )}
      <input
        id={inputId}
        readOnly={readOnly}
        required={required}
        className={cn(
          "block h-9 w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-card-foreground shadow-sm outline-none transition placeholder:text-muted-foreground",
          "focus:border-ring focus:ring-2 focus:ring-ring/20",
          "disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground",
          readOnly && "bg-muted text-muted-foreground",
          error && "border-destructive focus:border-destructive focus:ring-destructive/20",
          className
        )}
        {...props}
      />
      {(error || hint) && (
        <span className={cn("mt-1 block text-xs", error ? "text-destructive" : "text-muted-foreground")}>
          {error || hint}
        </span>
      )}
    </label>
  );
}
