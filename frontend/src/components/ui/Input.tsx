import type { InputHTMLAttributes } from "react";
import { cn } from "../../utils/cn";
import {
  fieldControlClass,
  fieldErrorClass,
  fieldHintClass,
  fieldLabelClass,
} from "./fieldStyles";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({
  label,
  error,
  hint,
  className,
  id,
  ...props
}: InputProps) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className={fieldLabelClass}>
          {label}
        </label>
      )}
      <input
        id={id}
        className={cn(
          fieldControlClass,
          error && "border-rose-500 focus:border-rose-500 focus:ring-rose-100",
          className
        )}
        aria-invalid={!!error}
        {...props}
      />
      {error ? (
        <p className={fieldErrorClass}>{error}</p>
      ) : (
        hint && <p className={fieldHintClass}>{hint}</p>
      )}
    </div>
  );
}
