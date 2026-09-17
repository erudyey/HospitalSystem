<script lang="ts">
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";

  interface Props extends HTMLAttributes<HTMLTableSectionElement> {
    class?: string;
    children?: Snippet;
  }

  let { class: className = "", children, ...restProps }: Props = $props();
</script>

<thead class={cn("bg-stone-50/80 [&_tr]:border-b border-stone-200", className)} {...restProps}>
  {@render children?.()}
</thead>
