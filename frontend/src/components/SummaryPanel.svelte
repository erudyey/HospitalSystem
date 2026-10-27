<script lang="ts">
  import { onMount, type Snippet } from "svelte";

  let { children, label = "Summary" }: { children: Snippet; label?: string } = $props();
  let open = $state(true);

  onMount(() => {
    const shortWindow = window.matchMedia("(max-height: 699px)");
    const update = () => { open = !shortWindow.matches; };
    update();
    shortWindow.addEventListener("change", update);
    return () => shortWindow.removeEventListener("change", update);
  });
</script>

<details bind:open class="summary-panel shrink-0">
  <summary class="cursor-pointer text-sm font-medium text-clinic">{label}</summary>
  <div class="summary-panel-content">{@render children()}</div>
</details>

<style>
  @media (min-height: 700px) {
    summary { display: none; }
  }
  @media (max-height: 699px) {
    .summary-panel-content { max-height: 25vh; overflow: auto; padding-top: 0.5rem; }
  }
</style>
