import { cn } from "../../utils/cn";

export function Spinner({
  className,
  label = "Loading",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <div className="inline-flex items-center justify-center" role="status" aria-live="polite">
      <div
        className={cn(
          "h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-b-sky-600",
          className
        )}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
