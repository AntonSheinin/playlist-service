import { type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  maxWidth?: string;
}

function mapMaxWidth(maxWidth: string): string {
  if (maxWidth.includes("6xl") || maxWidth.includes("7xl")) return "max-w-6xl";
  if (maxWidth.includes("4xl") || maxWidth.includes("5xl")) return "max-w-4xl";
  if (maxWidth.includes("2xl") || maxWidth.includes("3xl")) return "max-w-2xl";
  return "max-w-lg";
}

export function Modal({ open, onClose, title, children, footer, maxWidth = "max-w-lg" }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/70" />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg border border-border bg-card text-card-foreground shadow-xl",
            mapMaxWidth(maxWidth)
          )}
        >
          <Dialog.Title className="border-b border-border px-5 py-4 pr-12 text-lg font-semibold text-card-foreground">
            {title}
          </Dialog.Title>
          <Dialog.Close
            className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-muted hover:text-foreground"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Dialog.Close>
          <div className="min-h-0 flex-1 overflow-auto px-5 py-4">{children}</div>
          {footer && <div className="flex justify-end gap-2 border-t border-border px-5 py-4">{footer}</div>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
