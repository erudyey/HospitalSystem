<script lang="ts">
  import { cn } from "$lib/utils";
  import type { HTMLButtonAttributes } from "svelte/elements";

  interface Props extends HTMLButtonAttributes {
    variant?: "default" | "outline" | "secondary" | "ghost" | "destructive";
    size?: "default" | "sm" | "lg" | "icon";
    loading?: boolean;
    class?: string;
  }

  let {
    variant = "default",
    size = "default",
    loading = false,
    disabled = false,
    class: className = "",
    children,
    ...restProps
  }: Props = $props();

  const variantStyles = {
    default: "bg-[#0F766E] text-white hover:bg-[#0D9488] shadow-sm active:translate-y-[1px]",
    outline: "border border-stone-200 bg-white text-stone-800 hover:bg-stone-50 hover:border-stone-300 shadow-sm",
    secondary: "bg-stone-100 text-stone-800 hover:bg-stone-200",
    ghost: "text-stone-700 hover:bg-stone-100 hover:text-stone-900",
    destructive: "bg-rose-600 text-white hover:bg-rose-700 shadow-sm",
  };

  const sizeStyles = {
    default: "h-10 px-4 py-2 text-sm",
    sm: "h-8 px-3 text-xs rounded-md",
    lg: "h-11 px-6 text-base rounded-md",
    icon: "h-9 w-9 p-0",
  };
</script>

<button
  class={cn(
    "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0F766E] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer",
    variantStyles[variant],
    sizeStyles[size],
    className
  )}
  disabled={disabled || loading}
  {...restProps}
>
  {#if loading}
    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  {/if}
  {@render children?.()}
</button>
