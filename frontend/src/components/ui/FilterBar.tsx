import type { ReactNode } from "react";
import { Box, Paper } from "@mui/material";

interface FilterBarProps {
  children: ReactNode;
  className?: string;
}

export function FilterBar({ children }: FilterBarProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(4, minmax(0, 1fr))" },
          gap: 2,
        }}
      >
        {children}
      </Box>
    </Paper>
  );
}
