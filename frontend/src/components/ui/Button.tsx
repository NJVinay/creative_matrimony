import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
    size?: "sm" | "md" | "lg";
    isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = "primary", size = "md", isLoading, children, ...props }, ref) => {
        const baseStyles = "inline-flex items-center justify-center rounded-lg font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";

        // Contrast rules (FRONTEND_COMPETITOR_RESEARCH.md):
        // indigo buttons get white text; gold buttons get dark text —
        // never white on gold, never yellow text on pale surfaces.
        const variants = {
            primary: "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 shadow-sm",
            secondary: "bg-gold-400 text-gray-800 hover:bg-gold-600 active:bg-gold-700 shadow-sm",
            outline: "border border-primary-600 text-primary-600 hover:bg-primary-50 active:bg-primary-100 dark:border-primary-400 dark:text-primary-300 dark:hover:bg-primary-950",
            ghost: "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800",
            danger: "bg-danger text-white hover:bg-red-800",
        };

        const sizes = {
            sm: "h-8 px-3 text-sm",
            md: "h-10 px-4 py-2",
            lg: "h-12 px-6 text-lg",
        };

        return (
            <button
                ref={ref}
                className={cn(baseStyles, variants[variant], sizes[size], className)}
                disabled={isLoading || props.disabled}
                {...props}
            >
                {isLoading ? (
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                ) : null}
                {children}
            </button>
        );
    }
);
Button.displayName = "Button";

export { Button };
