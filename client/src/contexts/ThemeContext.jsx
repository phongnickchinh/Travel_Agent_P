import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext({ theme: 'light', toggleTheme: () => {}, setTheme: () => {} });

const STORAGE_KEY = 'tap_theme';

function getInitialTheme() {
  if (typeof window === 'undefined') return 'light';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  // console.log('[Theme] localStorage:', stored);
  if (stored === 'light' || stored === 'dark') {
    // console.log('[Theme] Using stored:', stored);
    return stored;
  }
  const systemPreference = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  // console.log('[Theme] Using system preference:', systemPreference);
  return systemPreference;
}

function applyThemeClass(theme) {
  const root = document.documentElement;
  // console.log('[Theme] Applying theme:', theme);
  if (theme === 'dark') {
    root.classList.add('dark');
    // console.log('[Theme] Added .dark class');
  } else {
    root.classList.remove('dark');
    // console.log('[Theme] Removed .dark class');
  }
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    // console.log('[Theme] State changed to:', theme);
    applyThemeClass(theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  // Keep in sync with system changes when user has not explicitly chosen
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (event) => {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') return;
      setTheme(event.matches ? 'dark' : 'light');
    };
    media.addEventListener('change', handler);
    return () => media.removeEventListener('change', handler);
  }, []);

  const value = useMemo(() => ({
    theme,
    setTheme,
    toggleTheme: () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark')),
  }), [theme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
