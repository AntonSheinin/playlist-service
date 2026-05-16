import { CircularProgress, Box } from "@mui/material";

export function Spinner({
  className,
  label = "Loading",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <Box className={className} component="span" role="status" aria-live="polite" sx={{ display: "inline-flex", alignItems: "center" }}>
      <CircularProgress size={28} aria-hidden="true" />
      <Box component="span" sx={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
        {label}
      </Box>
    </Box>
  );
}
