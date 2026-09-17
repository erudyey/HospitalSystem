<script lang="ts">
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";
  import type { HTMLTdAttributes } from "svelte/elements";

  interface Props extends HTMLTdAttributes {
    class?: string;
    children?: Snippet;
  }

  let { class: className = "", children, ...restProps }: Props = $props();
</script>

<td class={cn("p-4 align-middle text-stone-800 [&:has([role=checkbox])]:pr-0", className)} {...restProps}>
  {@render children?.()}
</td>
