import { Alert, IconButton, Stack } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useToast } from "../../hooks/useToast";

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  return (
    <Stack
      spacing={1}
      sx={{
        position: "fixed",
        right: 16,
        top: 16,
        zIndex: (theme) => theme.zIndex.snackbar,
        width: { xs: "calc(100% - 32px)", sm: 420 },
      }}
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <Alert
          key={toast.id}
          severity={toast.type}
          variant="filled"
          role={toast.type === "error" ? "alert" : "status"}
          action={
            <IconButton color="inherit" size="small" onClick={() => removeToast(toast.id)} aria-label="Dismiss notification">
              <CloseIcon fontSize="small" />
            </IconButton>
          }
          sx={{ width: "100%", boxShadow: 3 }}
        >
          {toast.message}
        </Alert>
      ))}
    </Stack>
  );
}
