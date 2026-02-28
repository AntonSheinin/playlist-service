import type { SelectHTMLAttributes } from "react";
import { cn } from "../../utils/cn";
import { fieldControlClass, fieldLabelClass } from "./fieldStyles";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export function Select({ label, className, id, children, ...props }: SelectProps) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className={fieldLabelClass}>
          {label}
        </label>
      )}
      <select
        id={id}
        className={cn(
          fieldControlClass,
          className
        )}
        {...props}
      >
        {children}
      </select>
    </div>
  );
}
