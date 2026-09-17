<script lang="ts">
  import { cn } from "$lib/utils";
  import type { HTMLInputAttributes } from "svelte/elements";

  interface Props extends HTMLInputAttributes {
    class?: string;
    value?: string | number;
    error?: boolean;
  }

  let {
    class: className = "",
    value = $bindable(),
    error = false,
    ...restProps
  }: Props = $props();
</script>

<input
  bind:value
  class={cn(
    "flex h-10 w-full rounded-md border bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors",
    error
      ? "border-rose-300 focus-visible:ring-rose-500 text-rose-900"
      : "border-stone-200 focus-visible:ring-[#0F766E] focus-visible:border-[#0F766E]",
    className
  )}
  {...restProps}
/>
