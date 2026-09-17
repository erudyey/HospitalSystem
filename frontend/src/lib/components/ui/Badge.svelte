<script lang="ts">
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";

  interface Props extends HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "scheduled" | "completed" | "cancelled" | "outline" | "id";
    class?: string;
    children?: Snippet;
  }

  let {
    variant = "default",
    class: className = "",
    children,
    ...restProps
  }: Props = $props();

  const variantStyles = {
    default: "bg-stone-100 text-stone-800 border-stone-200",
    id: "bg-teal-50 text-teal-800 border-teal-200 font-mono",
    scheduled: "bg-amber-50 text-amber-800 border-amber-200",
    completed: "bg-emerald-50 text-emerald-800 border-emerald-200",
    cancelled: "bg-rose-50 text-rose-800 border-rose-200",
    outline: "text-stone-800 border-stone-200",
  };
</script>

<div
  class={cn(
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors select-none",
    variantStyles[variant],
    className
  )}
  {...restProps}
>
  {@render children?.()}
</div>
