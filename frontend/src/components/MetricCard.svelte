<script lang="ts">
  import type { Users } from "lucide-svelte";
  import * as Card from "$lib/components/ui/card";

  interface Props {
    label: string;
    value: number | null;
    description: string;
    icon: typeof Users;
    loading?: boolean;
    unavailable?: boolean;
  }

  let { label, value, description, icon: Icon, loading = false, unavailable = false }: Props = $props();
</script>

<Card.Root class="metric-card" aria-busy={loading} data-testid="metric-card">
  <Card.Header class="p-3.5 pb-1">
    <div class="flex items-start justify-between gap-1.5 min-h-8">
      <Card.Title class="text-xs font-medium leading-4 text-muted-foreground min-w-0 break-words">{label}</Card.Title>
      <span class="size-5 rounded-md bg-info/10 text-info flex items-center justify-center shrink-0" aria-hidden="true">
        <Icon class="size-3.5" />
      </span>
    </div>
  </Card.Header>
  <Card.Content class="px-3.5 pt-0 pb-3.5">
    <p class="text-2xl font-semibold tracking-tight tabular-nums leading-tight">
      {#if loading || unavailable || value === null}
        <span aria-hidden="true">--</span>
        <span class="sr-only">{loading ? "Loading" : "Unavailable"}</span>
      {:else}
        {value.toLocaleString()}
      {/if}
    </p>
    <Card.Description class="text-[11px] leading-snug mt-1">{description}</Card.Description>
  </Card.Content>
</Card.Root>
