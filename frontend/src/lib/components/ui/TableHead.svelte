<script lang="ts">
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";
  import type { HTMLThAttributes } from "svelte/elements";

  interface Props extends HTMLThAttributes {
    class?: string;
    children?: Snippet;
  }

  let { class: className = "", children, ...restProps }: Props = $props();
</script>

<th
  class={cn(
    "h-10 px-4 text-left align-middle text-xs font-semibold uppercase tracking-wider text-stone-500 [&:has([role=checkbox])]:pr-0",
    className
  )}
  {...restProps}
>
  {@render children?.()}
</th>
