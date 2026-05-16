import { createTheme } from "@mui/material/styles";

export const drawerWidth = 248;

export const theme = createTheme({
  palette: {
    primary: {
      main: "#0284c7",
      dark: "#0369a1",
      light: "#38bdf8",
    },
    background: {
      default: "#f8fafc",
      paper: "#ffffff",
    },
    text: {
      primary: "#0f172a",
      secondary: "#475569",
    },
  },
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        "*:focus-visible": {
          outline: "2px solid #38bdf8",
          outlineOffset: 2,
        },
        body: {
          minHeight: "100vh",
          background: "#f8fafc",
        },
        "#root": {
          minHeight: "100vh",
        },
      },
    },
    MuiButton: {
      defaultProps: {
        size: "small",
      },
      styleOverrides: {
        root: {
          minHeight: 32,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        size: "small",
        variant: "outlined",
      },
    },
    MuiFormControl: {
      defaultProps: {
        size: "small",
      },
    },
    MuiSelect: {
      defaultProps: {
        size: "small",
      },
    },
    MuiTable: {
      defaultProps: {
        size: "small",
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          color: "#475569",
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          backgroundColor: "#f8fafc",
          whiteSpace: "nowrap",
        },
        body: {
          color: "#0f172a",
          fontSize: "0.875rem",
        },
      },
    },
    MuiCard: {
      defaultProps: {
        variant: "outlined",
      },
    },
    MuiChip: {
      defaultProps: {
        size: "small",
      },
    },
    MuiDialog: {
      defaultProps: {
        fullWidth: true,
      },
    },
  },
});
