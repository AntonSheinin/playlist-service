import { useMemo, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Check, ChevronsUpDown, Loader2, X } from "lucide-react";
import { cn } from "../../lib/utils";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "./Command";

export interface SelectOption {
  value: number;
  label: string;
}

interface MultiSelectProps {
  label?: string;
  options: SelectOption[];
  value: SelectOption[];
  onChange: (selected: SelectOption[]) => void;
  onInputChange?: (value: string) => void;
  placeholder?: string;
  isLoading?: boolean;
  isClearable?: boolean;
  noOptionsMessage?: (inputValue: string) => string;
  className?: string;
}

export function MultiSelect({
  label,
  options,
  value,
  onChange,
  onInputChange,
  placeholder = "Select...",
  isLoading,
  isClearable = true,
  noOptionsMessage,
  className,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const compact = !label;

  const visibleOptions = useMemo(() => {
    if (onInputChange || !query.trim()) return options;
    const normalized = query.trim().toLowerCase();
    return options.filter((option) => option.label.toLowerCase().includes(normalized));
  }, [onInputChange, options, query]);

  function setSearch(next: string) {
    setQuery(next);
    onInputChange?.(next);
  }

  function toggle(option: SelectOption) {
    const exists = value.some((selected) => selected.value === option.value);
    onChange(exists ? value.filter((selected) => selected.value !== option.value) : [...value, option]);
  }

  function clear() {
    onChange([]);
  }

  const chipValues = compact && value.length > 1 ? value.slice(0, 1) : value;
  const overflowCount = compact && value.length > 1 ? value.length - 1 : 0;

  return (
    <div className={cn("min-w-0", className)}>
      {label && (
        <span className="mb-1 block text-xs font-semibold uppercase tracking-normal text-muted-foreground">
          {label}
        </span>
      )}
      <div className="flex min-w-0 items-stretch gap-1">
        <Popover.Root open={open} onOpenChange={setOpen}>
          <Popover.Trigger asChild>
            <button
              type="button"
              className={cn(
                "flex min-w-0 flex-1 items-center justify-between gap-2 rounded-md border border-input bg-card text-left text-sm text-card-foreground shadow-sm outline-none transition",
                "focus:border-ring focus:ring-2 focus:ring-ring/20",
                compact ? "min-h-8 px-2 py-1 text-xs" : "min-h-9 px-3 py-2"
              )}
              role="combobox"
              aria-expanded={open}
              aria-haspopup="listbox"
            >
              <span className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
                {value.length === 0 ? (
                  <span className="truncate text-muted-foreground">{placeholder}</span>
                ) : (
                  <>
                    {chipValues.map((option) => (
                      <span
                        key={option.value}
                        className="status-info max-w-full truncate rounded-full border px-2 py-0.5 text-xs font-medium"
                      >
                        {option.label}
                      </span>
                    ))}
                    {overflowCount > 0 && (
                      <span className="status-neutral rounded-full border px-2 py-0.5 text-xs font-medium">
                        +{overflowCount}
                      </span>
                    )}
                  </>
                )}
              </span>
              <span className="flex shrink-0 items-center gap-1">
                {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" aria-hidden="true" />}
                <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              </span>
            </button>
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content
              align="start"
              sideOffset={4}
              className="z-[1500] max-h-[min(22rem,calc(100dvh-2rem))] w-[min(var(--radix-popover-trigger-width),calc(100vw-1rem))] overflow-hidden rounded-md border border-border bg-popover p-0 shadow-lg"
            >
              <Command shouldFilter={!onInputChange}>
                <CommandInput value={query} onValueChange={setSearch} placeholder="Search..." />
                <CommandList>
                  {isLoading ? (
                    <div className="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      Loading...
                    </div>
                  ) : visibleOptions.length === 0 ? (
                    <CommandEmpty>{noOptionsMessage ? noOptionsMessage(query) : "No options"}</CommandEmpty>
                  ) : (
                    <CommandGroup>
                      {visibleOptions.map((option) => {
                        const selected = value.some((item) => item.value === option.value);
                        return (
                          <CommandItem
                            key={option.value}
                            value={`${option.value}:${option.label}`}
                            onSelect={() => toggle(option)}
                            role="option"
                            aria-selected={selected}
                          >
                            <span
                              className={cn(
                                "mr-2 flex h-4 w-4 items-center justify-center rounded border",
                                selected ? "border-primary bg-primary text-primary-foreground" : "border-input"
                              )}
                            >
                              {selected && <Check className="h-3 w-3" aria-hidden="true" />}
                            </span>
                            <span className="truncate">{option.label}</span>
                          </CommandItem>
                        );
                      })}
                    </CommandGroup>
                  )}
                </CommandList>
              </Command>
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
        {isClearable && value.length > 0 && (
          <button
            type="button"
            className={cn(
              "inline-flex shrink-0 items-center justify-center rounded-md border border-border bg-card text-muted-foreground shadow-sm hover:bg-muted hover:text-foreground",
              compact ? "h-8 w-8" : "h-9 w-9"
            )}
            onClick={clear}
            aria-label="Clear selection"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
