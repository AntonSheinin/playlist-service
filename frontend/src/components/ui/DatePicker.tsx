import { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { DayPicker } from "react-day-picker";
import dayjs from "dayjs";
import { Calendar, X } from "lucide-react";
import { cn } from "../../lib/utils";

interface DatePickerProps {
  label?: string;
  selected: Date | null;
  onChange: (date: Date | null) => void;
  isClearable?: boolean;
  id?: string;
  placeholder?: string;
}

function toInputValue(date: Date | null): string {
  return date ? dayjs(date).format("YYYY-MM-DD") : "";
}

function parseInputDate(value: string): Date | null {
  if (!value) return null;
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.toDate() : null;
}

export function DatePicker({
  label,
  selected,
  onChange,
  isClearable = true,
  id,
  placeholder = "YYYY-MM-DD",
}: DatePickerProps) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      {label && (
        <label htmlFor={id} className="mb-1 block text-xs font-semibold uppercase tracking-normal text-muted-foreground">
          {label}
        </label>
      )}
      <div className="flex gap-2">
        <input
          id={id}
          type="date"
          value={toInputValue(selected)}
          onChange={(event) => onChange(parseInputDate(event.target.value))}
          placeholder={placeholder}
          className="block h-9 min-w-0 flex-1 rounded-md border border-input bg-card px-3 py-2 text-sm text-card-foreground shadow-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20"
        />
        {isClearable && selected && (
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground shadow-sm hover:bg-muted hover:text-foreground"
            onClick={() => onChange(null)}
            aria-label={label ? `Clear ${label}` : "Clear date"}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
        <Popover.Root open={open} onOpenChange={setOpen}>
          <Popover.Trigger asChild>
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground shadow-sm hover:bg-muted hover:text-foreground"
              aria-label={label ? `Open ${label} calendar` : "Open calendar"}
            >
              <Calendar className="h-4 w-4" aria-hidden="true" />
            </button>
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content
              align="end"
              sideOffset={4}
              className="z-[1500] rounded-md border border-border bg-popover p-3 text-popover-foreground shadow-lg"
            >
              <DayPicker
                mode="single"
                selected={selected ?? undefined}
                onSelect={(date) => {
                  onChange(date ?? null);
                  setOpen(false);
                }}
                classNames={{
                  month_caption: "mb-2 text-center text-sm font-semibold text-popover-foreground",
                  nav: "flex items-center justify-between gap-2",
                  button_previous: "rounded p-1 text-muted-foreground hover:bg-muted",
                  button_next: "rounded p-1 text-muted-foreground hover:bg-muted",
                  weekdays: "grid grid-cols-7 text-xs text-muted-foreground",
                  weekday: "p-1 text-center",
                  week: "grid grid-cols-7",
                  day: "p-0.5",
                  day_button: cn(
                    "h-8 w-8 rounded-md text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground",
                    "aria-selected:bg-primary aria-selected:text-primary-foreground"
                  ),
                  today: "font-semibold",
                }}
              />
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </div>
    </div>
  );
}
