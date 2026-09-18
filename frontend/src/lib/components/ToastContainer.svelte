<script lang="ts">
  import { toast } from "$lib/toast.svelte";
  import { CheckCircle2, AlertCircle, Info, X } from "lucide-svelte";
</script>

<div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full px-4 sm:px-0">
  {#each toast.toasts as item (item.id)}
    <div
      role="status"
      class="pointer-events-auto flex items-center justify-between gap-3 p-3.5 rounded-xl border bg-card text-card-foreground shadow-lg text-xs font-medium transition-all animate-in fade-in slide-in-from-bottom-2 duration-200"
    >
      <div class="flex items-center gap-2.5 min-w-0">
        {#if item.type === "success"}
          <CheckCircle2 class="size-4 text-emerald-600 shrink-0" />
        {:else if item.type === "error"}
          <AlertCircle class="size-4 text-destructive shrink-0" />
        {:else}
          <Info class="size-4 text-primary shrink-0" />
        {/if}
        <span class="truncate text-foreground leading-snug">{item.message}</span>
      </div>
      <button
        type="button"
        onclick={() => toast.dismiss(item.id)}
        class="text-muted-foreground hover:text-foreground p-1 rounded-md transition-colors cursor-pointer shrink-0"
        title="Dismiss"
      >
        <X class="size-3.5" />
        <span class="sr-only">Close</span>
      </button>
    </div>
  {/each}
</div>
