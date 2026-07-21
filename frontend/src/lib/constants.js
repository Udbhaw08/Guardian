// Single source of truth for display metadata, mirroring the backend's
// _POLICY_META / _SEVERITY_BAR and the /api/detectors catalog.

export const DECISIONS = ["ALLOW", "WARN_CONFIRM", "BLOCK"];

// Refined, muted status colors for an enterprise light SaaS theme
export const DECISION_META = {
  ALLOW: { label: "Allow", token: "allow", chartColor: "#059669" },
  WARN_CONFIRM: { label: "Warn / Confirm", token: "warn", chartColor: "#d97706" },
  BLOCK: { label: "Block", token: "block", chartColor: "#e11d48" },
};

export const SEVERITIES = ["critical", "high", "medium", "low"];

export const SEVERITY_META = {
  critical: { label: "Critical", dot: "🔴", chartColor: "#e11d48" },
  high: { label: "High", dot: "🟠", chartColor: "#ea580c" },
  medium: { label: "Medium", dot: "🟡", chartColor: "#d97706" },
  low: { label: "Low", dot: "🟢", chartColor: "#059669" },
  none: { label: "None", dot: "⚪", chartColor: "#64748b" },
};

import {
  KeyRound,
  CreditCard,
  Lock,
  Fingerprint,
  Landmark,
  ShieldAlert,
  FileKey,
  FileText,
  Image as ImageIcon,
  FileArchive,
  CircleHelp,
  ShieldCheck,
  Terminal,
} from "lucide-react";

// SVG icon + label per detector (enterprise styling)
export const DETECTOR_META = {
  api_key: { Icon: KeyRound, label: "Credentials / API Key" },
  credit_card: { Icon: CreditCard, label: "Payment Data / Credit Card" },
  cvv: { Icon: Lock, label: "Card CVV / CVC" },
  national_id: { Icon: Fingerprint, label: "National Identifier" },
  financial: { Icon: Landmark, label: "Financial Info" },
  prompt_injection: { Icon: Terminal, label: "Prompt Injection / Jailbreak" },
  env_file: { Icon: FileKey, label: "Environment / Secrets File" },
  pdf_prompt_injection: { Icon: FileText, label: "PDF Prompt Injection" },
  image_prompt_injection: { Icon: ImageIcon, label: "Image Prompt Injection" },
  zip_env_leak: { Icon: FileArchive, label: "ZIP Secrets Leak" },
  password: { Icon: ShieldAlert, label: "Password (legacy)" },
  download_error: { Icon: CircleHelp, label: "Image Download Error" },
};

export function detectorMeta(name) {
  return DETECTOR_META[name] || { Icon: CircleHelp, label: prettify(name) };
}

export function prettify(name) {
  if (!name) return "";
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// Harmonized, professional chart palette matching modern clean SaaS dashboards
export const CATEGORICAL_LIGHT = [
  "#3b82f6", // Soft Slate Blue
  "#10b981", // Soft Mint / Emerald
  "#6366f1", // Soft Indigo
  "#06b6d4", // Soft Cyan
  "#f43f5e", // Soft Coral
  "#f59e0b", // Soft Amber
  "#64748b", // Neutral Slate
  "#8b5cf6", // Soft Violet
];

export const CATEGORICAL_DARK = [
  "#60a5fa",
  "#34d399",
  "#818cf8",
  "#22d3ee",
  "#fb7185",
  "#fbbf24",
  "#94a3b8",
  "#a78bfa",
];

/** Return the categorical color for slot i in the active theme. */
export function categorical(i, isDark) {
  const arr = isDark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  return arr[i % arr.length];
}
