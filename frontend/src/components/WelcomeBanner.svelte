<script lang="ts">
  import type { StaffUser } from "$lib/api";
  import { formatClinicDate } from "$lib/calendar";
  import { Badge } from "$lib/components/ui/badge";
  import { CalendarDays, Stethoscope, Users } from "lucide-svelte";

  let { user, clinicNow, demoMode }: { user: StaffUser; clinicNow: string; demoMode: boolean } = $props();
</script>

<section class="staff-banner mb-4 flex items-center justify-between gap-4 rounded-xl border px-4 py-3 shrink-0" aria-label="Staff welcome">
  <div class="flex items-center gap-3 min-w-0">
    <span class="size-9 rounded-lg bg-clinic/10 text-clinic flex items-center justify-center shrink-0" aria-hidden="true">
      {#if user.role === "doctor"}<Stethoscope class="size-5" />{:else}<Users class="size-5" />{/if}
    </span>
    <div class="min-w-0">
      <h2 class="text-base font-semibold leading-snug break-words">Welcome, {user.full_name}</h2>
      <div class="mt-1 flex items-center flex-wrap gap-2">
        <Badge variant="clinic" class="text-[10px] font-medium">{user.role === "doctor" ? "Doctor" : "Receptionist"}</Badge>
        <p class="flex items-center gap-1.5 text-xs text-foreground/70">
          <CalendarDays class="size-3.5 shrink-0" aria-hidden="true" />{formatClinicDate(clinicNow)}
        </p>
      </div>
    </div>
  </div>
  {#if demoMode}<Badge variant="demo" class="shrink-0">Demo data</Badge>{/if}
</section>
