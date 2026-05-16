import { Box, Button, MenuItem, TextField, Typography } from "@mui/material";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
  perPage?: number;
  onPerPageChange?: (perPage: number) => void;
  label?: string;
}

const perPageOptions = [10, 20, 50, 100];

export function Pagination({
  page,
  pages,
  total,
  onPageChange,
  perPage,
  onPerPageChange,
  label = "items",
}: PaginationProps) {
  if (pages <= 1 && !onPerPageChange) return null;

  return (
    <Box sx={{ borderTop: 1, borderColor: "divider", px: 2, py: 1.5 }}>
      <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, justifyContent: "space-between", gap: 1.5 }}>
        <Box sx={{ display: "flex", flexDirection: { xs: "column", sm: "row" }, alignItems: { sm: "center" }, gap: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
            Page {page} of {pages} ({total} {label})
          </Typography>
          {onPerPageChange && perPage && (
            <TextField
              select
              value={perPage}
              onChange={(e) => onPerPageChange(Number(e.target.value))}
              sx={{ width: 140 }}
            >
              {perPageOptions.map((n) => (
                <MenuItem key={n} value={n}>
                  {n} per page
                </MenuItem>
              ))}
            </TextField>
          )}
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {onPerPageChange && (
            <Button variant="outlined" onClick={() => onPageChange(1)} disabled={page <= 1}>
              First
            </Button>
          )}
          <Button variant="outlined" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
            Previous
          </Button>
          <Button variant="outlined" onClick={() => onPageChange(page + 1)} disabled={page >= pages}>
            Next
          </Button>
          {onPerPageChange && (
            <Button variant="outlined" onClick={() => onPageChange(pages)} disabled={page >= pages}>
              Last
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
}
