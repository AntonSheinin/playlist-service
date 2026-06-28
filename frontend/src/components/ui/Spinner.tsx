import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

export function Spinner({
  className,
  label = "Loading",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <span className={cn("inline-flex items-center", className)} role="status" aria-live="polite">
      <Loader2 className="h-7 w-7 animate-spin text-primary" aria-hidden="true" />
      <span className="sr-only">
        {label}
      </span>
    </span>
  );
}
