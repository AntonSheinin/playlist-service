import type { ComponentPropsWithoutRef } from "react";
import { Command as CommandPrimitive } from "cmdk";
import { cn } from "../../lib/utils";

export function Command({ className, ...props }: ComponentPropsWithoutRef<typeof CommandPrimitive>) {
  return <CommandPrimitive className={cn("flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground", className)} {...props} />;
}

export function CommandInput({ className, ...props }: ComponentPropsWithoutRef<typeof CommandPrimitive.Input>) {
  return (
    <CommandPrimitive.Input
      className={cn("h-9 w-full border-b border-border bg-popover px-3 text-sm text-popover-foreground outline-none placeholder:text-muted-foreground", className)}
      {...props}
    />
  );
}

export function CommandList({ className, ...props }: ComponentPropsWithoutRef<typeof CommandPrimitive.List>) {
  return <CommandPrimitive.List className={cn("max-h-72 overflow-y-auto overflow-x-hidden", className)} {...props} />;
}

export function CommandEmpty({ className, ...props }: ComponentPropsWithoutRef<typeof CommandPrimitive.Empty>) {
  return <CommandPrimitive.Empty className={cn("py-6 text-center text-sm text-muted-foreground", className)} {...props} />;
}

export function CommandGroup({ className, ...props }: ComponentPropsWithoutRef<typeof CommandPrimitive.Group>) {
  return <CommandPrimitive.Group className={cn("p-1 text-popover-foreground", className)} {...props} />;
}

export function CommandItem({ className, ...props }: ComponentPropsWithoutRef<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      className={cn("flex cursor-default select-none items-center rounded px-2 py-1.5 text-sm outline-none data-[selected=true]:bg-muted", className)}
      {...props}
    />
  );
}
