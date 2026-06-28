import type { ReactNode, SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  id?: string;
  name?: string;
  label?: string;
  className?: string;
  children: ReactNode;
}

export function Select({ label, id, children, className, ...props }: SelectProps) {
  const selectId = id || props.name;

  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-xs font-semibold uppercase tracking-normal text-muted-foreground">
          {label}
          {props.required && <span className="text-destructive"> *</span>}
        </span>
      )}
      <span className="relative block">
        <select
          id={selectId}
          className={cn(
            "block h-10 w-full appearance-none rounded-md border border-input bg-card py-0 pl-3 pr-10 text-sm leading-10 text-card-foreground shadow-sm outline-none transition",
            "hover:border-ring",
            "focus:border-ring focus:ring-2 focus:ring-ring/20",
            "disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground",
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
      </span>
    </label>
  );
}
