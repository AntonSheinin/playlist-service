/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  type ReactNode,
} from "react";
import { toast } from "sonner";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
  exiting?: boolean;
}

interface ToastContextValue {
  toasts: Toast[];
  showToast: (message: string, type?: ToastType) => void;
  removeToast: (id: number) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const removeToast = useCallback((id: number) => {
    toast.dismiss(id);
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "info") => {
      toast[type](message);
    },
    []
  );

  return (
    <ToastContext.Provider value={{ toasts: [], showToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
}
