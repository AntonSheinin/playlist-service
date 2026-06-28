import { Toaster } from "sonner";
import { useTheme } from "../../hooks/useTheme";

export function ToastContainer() {
  const { theme } = useTheme();

  return (
    <Toaster
      richColors
      closeButton
      position="top-right"
      theme={theme}
      toastOptions={{
        className: "font-sans",
      }}
    />
  );
}
