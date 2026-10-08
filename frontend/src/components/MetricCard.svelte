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

<Card.Root aria-busy={loading} data-testid="metric-card">
  <Card.Header class="p-3.5 pb-1">
    <div class="flex items-start justify-between gap-2">
      <Card.Title class="text-xs font-medium leading-snug text-muted-foreground">{label}</Card.Title>
      <Icon class="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
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
