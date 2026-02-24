import { useState, useCallback } from "react";

type SortDir = "asc" | "desc";

interface SortState {
  sortBy: string;
  sortDir: SortDir;
}

export function useSortable(defaultSortBy: string, defaultSortDir: SortDir = "asc") {
  const [sort, setSort] = useState<SortState>({
    sortBy: defaultSortBy,
    sortDir: defaultSortDir,
  });

  const toggleSort = useCallback((field: string) => {
    setSort((prev) => {
      if (prev.sortBy === field) {
        return { sortBy: field, sortDir: prev.sortDir === "asc" ? "desc" : "asc" };
      }
      return { sortBy: field, sortDir: "asc" };
    });
  }, []);

  return { ...sort, toggleSort };
}
