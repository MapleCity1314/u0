import * as React from "react";

import { cn } from "@/lib/utils";

const Badge = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full border border-[#fde9df] bg-[#fff7f3] px-3 py-1 text-xs font-semibold text-[#ef7f52]",
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = "Badge";

export { Badge };
