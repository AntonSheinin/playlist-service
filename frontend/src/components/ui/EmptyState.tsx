import { Box, TableCell, TableRow, Typography } from "@mui/material";

interface EmptyStateProps {
  message?: string;
  colSpan?: number;
}

export function EmptyState({ message = "No data found", colSpan }: EmptyStateProps) {
  if (colSpan) {
    return (
      <TableRow>
        <TableCell colSpan={colSpan} align="center" sx={{ py: 4, color: "text.secondary" }}>
          {message}
        </TableCell>
      </TableRow>
    );
  }

  return (
    <Box sx={{ px: 2, py: 4, textAlign: "center" }}>
      <Typography color="text.secondary">{message}</Typography>
    </Box>
  );
}
