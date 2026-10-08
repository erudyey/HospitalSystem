<script lang="ts">
  import { onMount, onDestroy, untrack } from "svelte";
  import { api, saveCsvFile, type DailyReport, type StaffUser } from "$lib/api";
  import { isCalendarDate } from "$lib/calendar";
  import { createReportLoader, dailyReportCsv, dailyReportFilename } from "$lib/report";
  import { toast } from "$lib/toast.svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from "$lib/components/ui/table";
  import { Calendar, Users, CheckCircle2, XCircle, RefreshCw, Download } from "lucide-svelte";
  import MetricCard from "./MetricCard.svelte";

  let { user, clinicNow }: { user: StaffUser; clinicNow: string } = $props();
  let today = $state(true);
  let selectedDate = $state("");
  let report = $state<DailyReport | null>(null);
  let loading = $state(true);
  let fetching = $state(false);
  let exporting = $state(false);
  let errorMessage = $state<string | null>(null);
  let exportError = $state<string | null>(null);
  const loader = createReportLoader(api.reports.daily);
  let disposed = false;
  let displayDate = $derived(today ? report?.date ?? clinicNow.slice(0, 10) : selectedDate);

  async function refresh(silent = false, date: string | undefined = today ? undefined : selectedDate) {
    if (disposed || exporting || (silent && fetching)) return;
    if (date !== undefined && !isCalendarDate(date)) {
      loader.invalidate();
      report = null;
      fetching = false;
      loading = false;
      errorMessage = "Choose a valid report date.";
      return;
    }
    fetching = true;
    if (!silent) loading = true;
    const result = await loader.load(date);
    if (!result || disposed) return;
    report = result.report;
    errorMessage = result.error;
    fetching = false;
    loading = false;
  }

  $effect(() => {
    user.id;
    const date = today ? undefined : selectedDate;
    untrack(() => {
      loader.invalidate();
      report = null;
      errorMessage = null;
      exportError = null;
      void refresh(false, date);
    });
  });

  onMount(() => {
    const poll = setInterval(() => { if (!document.hidden) void refresh(true); }, 5000);
    const visible = () => { if (!document.hidden) void refresh(true); };
    document.addEventListener("visibilitychange", visible);
    return () => {
      clearInterval(poll);
      document.removeEventListener("visibilitychange", visible);
    };
  });
  onDestroy(() => { disposed = true; loader.invalidate(); });

  async function exportCsv() {
    if (!report || fetching || loading || exporting || errorMessage) return;
    const snapshot = report;
    exporting = true;
    exportError = null;
    try {
      const result = await saveCsvFile(dailyReportFilename(snapshot), dailyReportCsv(snapshot));
      if (disposed) return;
      if (result === "saved") toast.success("Daily report CSV saved.");
      else if (result === "downloaded") toast.info("Daily report CSV download started.");
      else toast.info("CSV save cancelled.");
    } catch (error) {
      if (!disposed) exportError = (error as { message?: string })?.message || "Unable to save the CSV. Try another destination.";
    } finally {
      if (!disposed) exporting = false;
    }
  }

  const columns = [
    ["appointments", "Appointments"], ["patients", "Patients"],
    ["scheduled", "Scheduled"], ["checked_in", "Checked in"],
    ["in_consultation", "In consultation"], ["completed", "Completed"], ["cancelled", "Cancelled"],
  ] as const;
</script>

<div class="flex flex-col gap-4 flex-1 min-h-0 min-w-0 overflow-hidden">
  <div class="flex items-start justify-between gap-3 shrink-0">
    <div>
      <h2 class="text-lg font-semibold tracking-tight">Daily report</h2>
      <p class="text-xs text-muted-foreground mt-1">Current statuses of appointments scheduled for the selected date.</p>
    </div>
    <Badge variant="outline" class="shrink-0">{user.role === "doctor" ? "My appointments" : "Whole clinic"}</Badge>
  </div>

  <div class="flex flex-wrap items-end gap-3 shrink-0">
    <div class="flex flex-col gap-1">
      <label for="report-date" class="text-xs font-medium">Report date</label>
      <Input id="report-date" type="date" class="h-9 w-40 text-xs" value={displayDate}
        disabled={exporting} aria-invalid={!today && !isCalendarDate(selectedDate)}
        onchange={(event) => { selectedDate = event.currentTarget.value; today = false; }} />
    </div>
    <Button variant={today ? "secondary" : "outline"} size="sm" disabled={exporting} onclick={() => today = true}>Today</Button>
    <div class="flex items-center gap-2 ml-auto">
      <Button variant="outline" size="sm" disabled={fetching || exporting} onclick={() => refresh()}>
        <RefreshCw data-icon="inline-start" class={fetching ? "animate-spin" : ""} />Refresh
      </Button>
      <Button variant="outline" size="sm" disabled={!report || fetching || loading || exporting || !!errorMessage} onclick={exportCsv}>
        <Download data-icon="inline-start" />{exporting ? "Saving..." : "Save CSV"}
      </Button>
    </div>
  </div>

  <div class="grid grid-cols-4 gap-3 shrink-0">
    <MetricCard label="Appointments" value={report?.totals.appointments ?? null} description="All five appointment states" icon={Calendar} {loading} unavailable={!!errorMessage} />
    <MetricCard label="Patients on schedule" value={report?.totals.patients ?? null} description="Distinct patients, all statuses" icon={Users} {loading} unavailable={!!errorMessage} />
    <MetricCard label="Completed visits" value={report?.totals.completed ?? null} description="Finalized appointments" icon={CheckCircle2} {loading} unavailable={!!errorMessage} />
    <MetricCard label="Cancelled visits" value={report?.totals.cancelled ?? null} description="Cancelled appointments" icon={XCircle} {loading} unavailable={!!errorMessage} />
  </div>

  {#if errorMessage}<p role="alert" class="text-sm text-destructive shrink-0">{errorMessage} Select Refresh to try again.</p>{/if}
  {#if exportError}<p role="alert" class="text-sm text-destructive shrink-0">{exportError}</p>{/if}

  <div class="rounded-xl border bg-card shadow-sm overflow-hidden flex flex-col flex-1 min-h-0 min-w-0">
    <Table containerClass="flex-1 min-h-0 overflow-auto" class="text-xs min-w-[850px]">
      <TableHeader class="sticky top-0 bg-card z-10">
        <TableRow>
          <TableHead class="min-w-36">Doctor</TableHead>
          {#each columns as [, label]}<TableHead class="text-right">{label}</TableHead>{/each}
        </TableRow>
      </TableHeader>
      <TableBody>
        {#if report}
          <TableRow class="bg-muted/40 font-semibold">
            <TableCell>Overall total</TableCell>
            {#each columns as [key]}<TableCell class="text-right tabular-nums">{report.totals[key]}</TableCell>{/each}
          </TableRow>
          {#each report.doctors as doctor (doctor.doctor_id)}
            <TableRow>
              <TableCell class="font-medium break-words max-w-60">{doctor.doctor_name}</TableCell>
              {#each columns as [key]}<TableCell class="text-right tabular-nums">{doctor[key]}</TableCell>{/each}
            </TableRow>
          {/each}
          {#if report.doctors.length === 0}
            <TableRow><TableCell colspan={8} class="text-center py-10 text-muted-foreground">No appointments scheduled for this date.</TableCell></TableRow>
          {/if}
        {:else}
          <TableRow><TableCell colspan={8} class="text-center py-10 text-muted-foreground">{loading ? "Loading the selected date..." : "The report is unavailable."}</TableCell></TableRow>
        {/if}
      </TableBody>
    </Table>
    <div class="border-t px-4 py-3 text-[11px] text-muted-foreground shrink-0 flex flex-col gap-1">
      <p>A patient seeing two doctors counts once in the overall total.</p>
      <p>{#if report}Updated {report.generated_at.slice(11, 19)} (clinic time) · {report.date} · {report.mode === "demo" ? "Demo data" : "Clinic data"}{:else}The report refreshes every 5 seconds while visible.{/if}</p>
    </div>
  </div>
</div>
