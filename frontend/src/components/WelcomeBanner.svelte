<script lang="ts">
  import type { StaffUser } from "$lib/api";
  import { formatClinicDate } from "$lib/calendar";
  import { Badge } from "$lib/components/ui/badge";

  let { user, clinicNow, demoMode }: { user: StaffUser; clinicNow: string; demoMode: boolean } = $props();
</script>

<section class="mb-4 flex items-center justify-between gap-4 rounded-xl border bg-card px-4 py-3 shrink-0" aria-label="Staff welcome">
  <div class="min-w-0">
    <h2 class="text-base font-semibold leading-snug break-words">Welcome, {user.full_name}</h2>
    <p class="mt-1 text-xs text-muted-foreground">
      {user.role === "doctor" ? "Doctor" : "Receptionist"}
      <span class="mx-1.5" aria-hidden="true">·</span>
      {formatClinicDate(clinicNow)}
    </p>
  </div>
  {#if demoMode}<Badge variant="secondary" class="shrink-0">Demo data</Badge>{/if}
</section>
