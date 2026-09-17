<script lang="ts">
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";

  interface Props extends HTMLAttributes<HTMLTableRowElement> {
    class?: string;
    children?: Snippet;
  }

  let { class: className = "", children, ...restProps }: Props = $props();
</script>

<tr
  class={cn(
    "border-b border-stone-100 transition-colors hover:bg-stone-50/60 data-[state=selected]:bg-stone-100",
    className
  )}
  {...restProps}
>
  {@render children?.()}
</tr>
