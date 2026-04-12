import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "outline" | "accent";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-[var(--color-card)] text-[var(--color-foreground)]",
    outline: "border border-[var(--color-border)] bg-transparent",
    accent:
      "bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/30",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium font-mono",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
