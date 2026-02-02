import * as React from "react";

import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
}

const variantClasses = {
  default: "bg-[#111827] text-white hover:bg-[#0f172a]",
  outline: "border border-[#111827]/20 text-[#111827] hover:border-[#111827]/40 hover:bg-white",
  ghost: "text-[#111827] hover:bg-[#f8fafc]",
};

const sizeClasses = {
  sm: "h-9 px-3 text-sm",
  default: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-2xl font-semibold transition",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";

export { Button };
