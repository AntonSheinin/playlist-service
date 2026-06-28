import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ThemeContext, type Theme } from "./theme-context";

const STORAGE_KEY = "rutv-admin-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function isTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

function getSystemTheme(): Theme {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;

  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return isTheme(value) ? value : null;
  } catch {
    return null;
  }
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;

  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

function getInitialThemeState() {
  const storedTheme = getStoredTheme();
  return {
    hasStoredPreference: storedTheme !== null,
    theme: storedTheme ?? getSystemTheme(),
  };
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [initialState] = useState(getInitialThemeState);
  const [hasStoredPreference, setHasStoredPreference] = useState(initialState.hasStoredPreference);
  const [theme, setTheme] = useState<Theme>(initialState.theme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (hasStoredPreference || typeof window === "undefined" || !window.matchMedia) return;

    const media = window.matchMedia(DARK_QUERY);
    const handleChange = (event: MediaQueryListEvent) => {
      setTheme(event.matches ? "dark" : "light");
    };

    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, [hasStoredPreference]);

  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => {
      const nextTheme = currentTheme === "dark" ? "light" : "dark";

      try {
        if (typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, nextTheme);
        }
      } catch {
        // Theme switching should still work for this session if storage is unavailable.
      }

      setHasStoredPreference(true);
      return nextTheme;
    });
  }, []);

  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
