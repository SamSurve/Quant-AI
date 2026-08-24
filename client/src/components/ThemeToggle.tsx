/**
 * Research Observatory visual contract: a compact command-bar control for the
 * user’s durable light, dark, or system research environment preference.
 */

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type ThemePreference } from "@/contexts/ThemeContext";

const options: Array<{ value: ThemePreference; label: string; Icon: typeof Sun }> = [
  { value: "light", label: "Light theme", Icon: Sun },
  { value: "dark", label: "Dark theme", Icon: Moon },
  { value: "system", label: "System theme", Icon: Monitor },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="theme-toggle" role="group" aria-label="Color theme">
      {options.map(({ value, label, Icon }) => (
        <button key={value} type="button" onClick={() => setTheme(value)} aria-label={label} aria-pressed={theme === value} className={theme === value ? "is-active" : ""}>
          <Icon className="size-3.5" aria-hidden="true" />
          <span className="sr-only">{label}</span>
        </button>
      ))}
    </div>
  );
}
