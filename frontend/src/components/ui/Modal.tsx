import { type ReactNode } from "react";
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  maxWidth?: string;
}

function mapMaxWidth(maxWidth: string): "xs" | "sm" | "md" | "lg" | "xl" {
  if (maxWidth.includes("2xl") || maxWidth.includes("3xl")) return "md";
  if (maxWidth.includes("4xl") || maxWidth.includes("5xl")) return "lg";
  if (maxWidth.includes("6xl") || maxWidth.includes("7xl")) return "xl";
  return "sm";
}

export function Modal({ open, onClose, title, children, footer, maxWidth = "max-w-lg" }: ModalProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth={mapMaxWidth(maxWidth)} fullWidth>
      <DialogTitle sx={{ pr: 6 }}>
        {title}
        <IconButton
          aria-label="Close dialog"
          onClick={onClose}
          size="small"
          sx={{ position: "absolute", right: 12, top: 12 }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>{children}</DialogContent>
      {footer && <DialogActions>{footer}</DialogActions>}
    </Dialog>
  );
}
