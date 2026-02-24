import { useState, useCallback, useRef, useEffect } from "react";

type Widths = Record<string, number>;

export function useColumnResize(storageKey: string) {
  const [widths, setWidths] = useState<Widths>(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch {
      return {};
    }
  });

  const widthsRef = useRef(widths);
  useEffect(() => {
    widthsRef.current = widths;
  }, [widths]);

  const onResize = useCallback(
    (colKey: string, width: number) => {
      setWidths((prev) => {
        const next = { ...prev, [colKey]: width };
        try {
          localStorage.setItem(storageKey, JSON.stringify(next));
        } catch {
          // Ignore storage failures
        }
        return next;
      });
    },
    [storageKey]
  );

  const getWidth = useCallback(
    (colKey: string, fallback?: number): number | undefined => {
      return widthsRef.current[colKey] ?? fallback;
    },
    []
  );

  return { widths, getWidth, onResize };
}
