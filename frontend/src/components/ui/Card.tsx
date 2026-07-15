import { HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    glass?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
    ({ className, glass = false, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    "rounded-xl p-6 transition-all duration-200",
                    // Calm surfaces: white card, soft sand border, minimal shadow
                    glass ? "glass dark:glass-dark" : "bg-white dark:bg-gray-900 shadow-sm border border-sand dark:border-gray-800",
                    className
                )}
                {...props}
            />
        );
    }
);
Card.displayName = "Card";

export { Card };
