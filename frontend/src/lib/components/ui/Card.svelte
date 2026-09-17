<script lang="ts">
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";

  interface Props extends HTMLAttributes<HTMLDivElement> {
    class?: string;
    children?: Snippet;
  }

  let { class: className = "", children, ...restProps }: Props = $props();
</script>

<div
  class={cn(
    "rounded-xl border border-stone-200 bg-white text-stone-900 shadow-sm",
    className
  )}
  {...restProps}
>
  {@render children?.()}
</div>
