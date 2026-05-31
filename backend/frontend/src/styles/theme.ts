export const theme = {
  colors: {
    primary: "#2563eb",
    primaryHover: "#1d4ed8",
    primaryLight: "#3b82f6",

    background: "#0f172a",
    surface: "#1e293b",
    surfaceHover: "#334155",

    textPrimary: "#f8fafc",
    textSecondary: "#94a3b8",
    textMuted: "#64748b",

    success: "#22c55e",
    successLight: "#86efac",
    danger: "#ef4444",
    dangerLight: "#fca5a5",
    warning: "#f59e0b",
    warningLight: "#fcd34d",
    info: "#06b6d4",
    infoLight: "#67e8f9",

    border: "#334155",
    borderLight: "#475569",

    overlay: "rgba(15, 23, 42, 0.8)",
  },

  radius: {
    sm: "6px",
    md: "10px",
    lg: "16px",
    xl: "24px",
  },

  spacing: {
    xs: "4px",
    sm: "8px",
    md: "16px",
    lg: "24px",
    xl: "32px",
    "2xl": "48px",
  },

  shadows: {
    sm: "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
    md: "0 4px 6px -1px rgba(0, 0, 0, 0.4)",
    lg: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
    glow: "0 0 20px rgba(37, 99, 235, 0.3)",
  },

  transitions: {
    fast: "150ms cubic-bezier(0.4, 0, 0.2, 1)",
    base: "200ms cubic-bezier(0.4, 0, 0.2, 1)",
    slow: "300ms cubic-bezier(0.4, 0, 0.2, 1)",
  },
} as const;

export type Theme = typeof theme;
