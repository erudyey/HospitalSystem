<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    api,
    type Patient,
    type Appointment,
    type StaffUser,
    type MedicalRecord,
    type DoctorQueueResponse,
    type ApiError,
  } from "$lib/api";
  import { toast } from "$lib/toast.svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import * as Tabs from "$lib/components/ui/tabs";
  import {
    Table,
    TableHeader,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
  } from "$lib/components/ui/table";
  import ConsultationDialog from "./ConsultationDialog.svelte";
  import PatientChartDialog from "./PatientChartDialog.svelte";
  import {
    Stethoscope,
    Users,
    Clock,
    CheckCircle2,
    Calendar,
    FileText,
    RefreshCw,
    Search,
    UserCheck,
    Play,
    Pill,
    X,
    Loader2,
    AlertCircle,
  } from "lucide-svelte";

  interface Props {
    activeDoctor: StaffUser;
  }

  let { activeDoctor }: Props = $props();

  // Active Tab
  type DoctorTab = "queue" | "schedule" | "patients" | "notes";
  let activeTab = $state<DoctorTab>("queue");

  // Queue Data
  let checkedInQueue = $state<Appointment[]>([]);
  let inConsultationQueue = $state<Appointment[]>([]);
  let scheduledToday = $state<Appointment[]>([]);
  let completedToday = $state<Appointment[]>([]);

  // Patients & Notes collections
  let myPatients = $state<Patient[]>([]);
  let patientSearch = $state("");

  let clinicalNotes = $state<MedicalRecord[]>([]);
  let notesSearch = $state("");

  let isLoading = $state(false);
  let errorMessage = $state<string | null>(null);

  // Dialog State
  let isConsultationOpen = $state(false);
  let selectedAppointmentForConsult = $state<Appointment | null>(null);

  let isChartOpen = $state(false);
  let selectedPatientForChart = $state<Patient | null>(null);

  // Polling Timer (5-second queue refresh)
  let pollInterval: ReturnType<typeof setInterval> | null = null;

  function formatTime(timeStr?: string): string {
    if (!timeStr) return "--:--";
    const parts = timeStr.split(":");
    if (parts.length < 2) return timeStr;
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return timeStr;
    const ampm = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 || 12;
    const mm = m.toString().padStart(2, "0");
    return `${h12}:${mm} ${ampm}`;
  }

  async function loadDoctorQueue(silent = false) {
    if (!silent) isLoading = true;
    try {
      const res = await api.clinical.getDoctorQueue(activeDoctor.id);
      checkedInQueue = res.queue.checked_in;
      inConsultationQueue = res.queue.in_consultation;
      scheduledToday = res.queue.scheduled;
      completedToday = res.queue.completed;
      errorMessage = null;
    } catch (err) {
      const e = err as ApiError;
      if (!silent) {
        errorMessage = e.message || "Failed to load doctor queue.";
      }
    } finally {
      if (!silent) isLoading = false;
    }
  }

  async function loadMyPatients() {
    try {
      myPatients = await api.clinical.getDoctorPatients(activeDoctor.id, patientSearch || undefined);
    } catch {
      // Non-blocking
    }
  }

  async function reloadAll() {
    await Promise.all([loadDoctorQueue(), loadMyPatients()]);
  }

  function startPolling() {
    stopPolling();
    pollInterval = setInterval(() => {
      // Pause polling if consultation dialog is open or window is blurred
      if (isConsultationOpen || document.hidden) return;
      loadDoctorQueue(true);
    }, 5000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  async function handleBeginConsultation(app: Appointment) {
    try {
      if (app.status !== "In Consultation") {
        await api.updateAppointmentStatus(app.id, "In Consultation");
      }
      selectedAppointmentForConsult = app;
      isConsultationOpen = true;
      await loadDoctorQueue(true);
    } catch (err) {
      const e = err as ApiError;
      toast.error(`Unable to start consultation: ${e.message}`);
    }
  }

  function openPatientChart(patient: Patient) {
    selectedPatientForChart = patient;
    isChartOpen = true;
  }

  function openChartFromAppointment(app: Appointment) {
    selectedPatientForChart = {
      id: app.patient_id,
      full_name: app.patient_name,
      contact: "",
      age: 0,
    };
    isChartOpen = true;
  }

  let filteredMyPatients = $derived.by(() => {
    if (!patientSearch.trim()) return myPatients;
    const q = patientSearch.toLowerCase().trim();
    return myPatients.filter(
      (p) =>
        p.full_name.toLowerCase().includes(q) ||
        String(p.id).includes(q) ||
        (p.contact && p.contact.toLowerCase().includes(q))
    );
  });

  onMount(() => {
    reloadAll();
    startPolling();

    const handleVisibilityChange = () => {
      if (!document.hidden && !isConsultationOpen) {
        loadDoctorQueue(true);
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  });

  onDestroy(() => {
    stopPolling();
  });
</script>

<div class="flex flex-col gap-4 flex-1 min-h-0 overflow-hidden">
  <!-- Physician Header & Metrics Bar -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 shrink-0">
    <!-- Waiting Room Card -->
    <div class="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 sm:p-4 shadow-xs">
      <div class="flex items-center justify-between">
        <p class="text-[11px] sm:text-xs font-semibold text-amber-700 uppercase tracking-wider">Waiting Room</p>
        <span class="size-2 rounded-full bg-amber-500 animate-pulse"></span>
      </div>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{checkedInQueue.length}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Patients checked in & waiting</p>
    </div>

    <!-- Consulting Now Card -->
    <div class="rounded-xl border border-primary/30 bg-primary/5 p-3.5 sm:p-4 shadow-xs">
      <div class="flex items-center justify-between">
        <p class="text-[11px] sm:text-xs font-semibold text-primary uppercase tracking-wider">In Consultation</p>
        <span class="size-2 rounded-full bg-primary animate-ping"></span>
      </div>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{inConsultationQueue.length}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Active patient session</p>
    </div>

    <!-- Scheduled Today Card -->
    <div class="rounded-xl border bg-card text-card-foreground p-3.5 sm:p-4 shadow-xs">
      <p class="text-[11px] sm:text-xs font-medium text-muted-foreground uppercase tracking-wider">Scheduled Today</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{scheduledToday.length}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Pending arrival</p>
    </div>

    <!-- Completed Today Card -->
    <div class="rounded-xl border bg-card text-card-foreground p-3.5 sm:p-4 shadow-xs">
      <p class="text-[11px] sm:text-xs font-medium text-muted-foreground uppercase tracking-wider">Seen Today</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{completedToday.length}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Completed & signed visits</p>
    </div>
  </div>

  <!-- Workspace Tabs Navigation & Refresh -->
  <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 shrink-0">
    <Tabs.Root
      value={activeTab}
      onValueChange={(val) => {
        if (val) activeTab = val as DoctorTab;
      }}
    >
      <Tabs.List class="h-10 p-1">
        <Tabs.Trigger value="queue" class="px-3.5 text-xs font-medium gap-1.5">
          <UserCheck class="size-3.5" />
          <span>Waiting Room ({checkedInQueue.length + inConsultationQueue.length})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="schedule" class="px-3.5 text-xs font-medium gap-1.5">
          <Calendar class="size-3.5" />
          <span>Today's Schedule ({scheduledToday.length + checkedInQueue.length + inConsultationQueue.length + completedToday.length})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="patients" class="px-3.5 text-xs font-medium gap-1.5">
          <Users class="size-3.5" />
          <span>My Patients ({myPatients.length})</span>
        </Tabs.Trigger>
      </Tabs.List>
    </Tabs.Root>

    <div class="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        class="h-9 px-3 text-xs cursor-pointer"
        onclick={reloadAll}
        disabled={isLoading}
      >
        <RefreshCw class="size-3.5 mr-1.5 {isLoading ? 'animate-spin' : ''}" />
        Sync Queue
      </Button>
    </div>
  </div>

  <!-- Tab 1: Waiting Room Triage Queue -->
  {#if activeTab === "queue"}
    <div class="flex flex-col gap-4 flex-1 min-h-0 overflow-y-auto pr-1">
      <!-- Active Consultation Banner (if patient is currently consulting) -->
      {#if inConsultationQueue.length > 0}
        <div class="rounded-xl border border-primary/30 bg-primary/5 p-4 shadow-xs flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="size-2 rounded-full bg-primary animate-ping"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-primary">
                Active Consultation In Progress
              </span>
            </div>
            <span class="text-xs text-muted-foreground font-mono">
              {inConsultationQueue.length} patient session active
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            {#each inConsultationQueue as activeApp (activeApp.id)}
              <div class="rounded-lg border bg-card p-3.5 shadow-2xs flex flex-col justify-between gap-3">
                <div>
                  <div class="flex items-start justify-between">
                    <div>
                      <h4 class="text-sm font-semibold text-foreground">{activeApp.patient_name}</h4>
                      <p class="text-xs text-muted-foreground font-mono">Patient #{activeApp.patient_id} • Appt #{activeApp.id}</p>
                    </div>
                    <Badge variant="default" class="text-xs">
                      Consulting
                    </Badge>
                  </div>
                  {#if activeApp.reason_for_visit}
                    <p class="text-xs text-muted-foreground mt-2 italic">
                      Chief Complaint: {activeApp.reason_for_visit}
                    </p>
                  {/if}
                </div>

                <div class="flex items-center justify-between pt-2 border-t border-border/60">
                  <Button
                    variant="ghost"
                    size="sm"
                    class="h-7 text-xs px-2 text-muted-foreground hover:text-foreground cursor-pointer"
                    onclick={() => openChartFromAppointment(activeApp)}
                  >
                    <FileText class="size-3.5 mr-1" />
                    View Chart
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    class="h-7 text-xs px-3 cursor-pointer"
                    onclick={() => handleBeginConsultation(activeApp)}
                  >
                    Resume Consultation
                  </Button>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Waiting Room Cards -->
      <div class="rounded-xl border bg-card p-5 shadow-xs">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold text-foreground">Waiting Room Triage</h3>
            <Badge variant="secondary" class="text-xs font-semibold">
              {checkedInQueue.length} Waiting
            </Badge>
          </div>
          <span class="text-xs text-muted-foreground">Auto-updates every 5s</span>
        </div>

        {#if checkedInQueue.length === 0}
          <div class="flex flex-col items-center justify-center py-12 text-center text-muted-foreground gap-2">
            <UserCheck class="size-10 text-muted-foreground/40" />
            <p class="text-sm font-medium text-foreground">The Waiting Room is Clear</p>
            <p class="text-xs max-w-sm">
              No patients are currently checked in for consultation. When the front desk marks an appointment as 'Checked In', it will appear here immediately.
            </p>
          </div>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {#each checkedInQueue as app, idx (app.id)}
              <div class="rounded-xl border bg-card p-4 shadow-xs flex flex-col justify-between gap-3 hover:border-primary/40 transition-colors">
                <div>
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="size-5 rounded-full bg-secondary text-secondary-foreground font-bold text-xs flex items-center justify-center">
                          {idx + 1}
                        </span>
                        <h4 class="text-sm font-semibold text-foreground">{app.patient_name}</h4>
                      </div>
                      <p class="text-xs text-muted-foreground font-mono mt-0.5 pl-7">
                        Record #{app.patient_id} • Appt #{app.id}
                      </p>
                    </div>

                    <Badge variant="secondary" class="text-[11px] font-medium shrink-0">
                      Checked In
                    </Badge>
                  </div>

                  <!-- Time & Complaint -->
                  <div class="mt-3 pl-7 flex flex-col gap-1.5 text-xs">
                    <div class="flex items-center gap-1.5 text-muted-foreground">
                      <Clock class="size-3 text-muted-foreground shrink-0" />
                      <span>Scheduled: <strong>{formatTime(app.app_time)}</strong></span>
                    </div>
                    {#if app.reason_for_visit}
                      <div class="rounded bg-muted/40 p-2 text-xs italic text-foreground border border-border/40">
                        "{app.reason_for_visit}"
                      </div>
                    {/if}
                  </div>
                </div>

                <!-- Card Actions -->
                <div class="flex items-center justify-between pt-3 border-t border-border/60">
                  <Button
                    variant="outline"
                    size="sm"
                    class="h-8 text-xs px-2.5 cursor-pointer"
                    onclick={() => openChartFromAppointment(app)}
                  >
                    <FileText class="size-3.5 mr-1" />
                    Chart
                  </Button>

                  <Button
                    variant="default"
                    size="sm"
                    class="h-8 text-xs px-3 font-medium cursor-pointer"
                    onclick={() => handleBeginConsultation(app)}
                  >
                    <Play class="size-3.5 mr-1" />
                    Begin Consultation
                  </Button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

  <!-- Tab 2: Today's Full Schedule -->
  {:else if activeTab === "schedule"}
    <div class="rounded-xl border bg-card text-card-foreground shadow-xs overflow-hidden flex flex-col flex-1 min-h-0">
      <Table containerClass="flex-1 min-h-0 overflow-y-auto">
        <TableHeader class="sticky top-0 bg-card z-10 shadow-xs border-b [&_tr]:bg-card">
          <TableRow>
            <TableHead class="w-20">Appt #</TableHead>
            <TableHead>Patient</TableHead>
            <TableHead class="w-32">Time</TableHead>
            <TableHead>Chief Complaint</TableHead>
            <TableHead class="w-32 text-center">Status</TableHead>
            <TableHead class="w-24 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {#each [...inConsultationQueue, ...checkedInQueue, ...scheduledToday, ...completedToday] as item (item.id)}
            <TableRow>
              <TableCell class="font-mono text-xs text-muted-foreground">#{item.id}</TableCell>
              <TableCell class="font-medium text-foreground">
                {item.patient_name}
                <span class="text-xs text-muted-foreground font-normal ml-1">(#{item.patient_id})</span>
              </TableCell>
              <TableCell class="font-mono text-xs text-muted-foreground">
                {formatTime(item.app_time)}
              </TableCell>
              <TableCell class="text-xs text-muted-foreground italic">
                {item.reason_for_visit || "--"}
              </TableCell>
              <TableCell class="text-center">
                {#if item.status === "Checked In"}
                  <Badge variant="secondary" class="text-xs">
                    Checked In
                  </Badge>
                {:else if item.status === "In Consultation"}
                  <Badge variant="default" class="text-xs">
                    Consulting
                  </Badge>
                {:else if item.status === "Completed"}
                  <Badge variant="outline" class="text-xs">
                    Completed
                  </Badge>
                {:else}
                  <Badge variant="outline" class="text-xs text-muted-foreground">
                    Scheduled
                  </Badge>
                {/if}
              </TableCell>
              <TableCell class="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-7 text-xs px-2 cursor-pointer"
                  onclick={() => openChartFromAppointment(item)}
                >
                  Chart
                </Button>
              </TableCell>
            </TableRow>
          {/each}
        </TableBody>
      </Table>
    </div>

  <!-- Tab 3: My Patients Roster -->
  {:else if activeTab === "patients"}
    <div class="flex flex-col gap-3 flex-1 min-h-0 overflow-hidden">
      <div class="flex items-center justify-between gap-3 shrink-0">
        <div class="relative w-full sm:w-72">
          <Search class="absolute left-3 top-2.5 size-4 text-muted-foreground pointer-events-none" />
          <Input
            type="text"
            placeholder="Search patient name or ID..."
            bind:value={patientSearch}
            class="pl-9 h-9 text-xs"
          />
        </div>
      </div>

      <div class="rounded-xl border bg-card text-card-foreground shadow-xs overflow-hidden flex flex-col flex-1 min-h-0">
        <Table containerClass="flex-1 min-h-0 overflow-y-auto">
          <TableHeader class="sticky top-0 bg-card z-10 shadow-xs border-b [&_tr]:bg-card">
            <TableRow>
              <TableHead class="w-20">ID</TableHead>
              <TableHead>Full Name</TableHead>
              <TableHead class="w-20">Age</TableHead>
              <TableHead>Contact Detail</TableHead>
              <TableHead class="w-32 text-center">Visits with Me</TableHead>
              <TableHead class="w-28 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {#if filteredMyPatients.length === 0}
              <TableRow>
                <TableCell colspan={6} class="h-28 text-center text-xs text-muted-foreground">
                  No patient records match your search.
                </TableCell>
              </TableRow>
            {:else}
              {#each filteredMyPatients as p (p.id)}
                <TableRow>
                  <TableCell class="font-mono text-xs text-muted-foreground">#{p.id}</TableCell>
                  <TableCell class="font-medium text-foreground">{p.full_name}</TableCell>
                  <TableCell class="text-xs text-muted-foreground">{p.age} yrs</TableCell>
                  <TableCell class="text-xs text-muted-foreground font-mono">{p.contact || "--"}</TableCell>
                  <TableCell class="text-center text-xs font-medium text-foreground">
                    {p.appointment_count || 1}
                  </TableCell>
                  <TableCell class="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      class="h-7 text-xs px-2 cursor-pointer"
                      onclick={() => openPatientChart(p)}
                    >
                      <FileText class="size-3 mr-1 text-primary" />
                      View Chart
                    </Button>
                  </TableCell>
                </TableRow>
              {/each}
            {/if}
          </TableBody>
        </Table>
      </div>
    </div>
  {/if}

  <!-- Consultation Dialog (SOAP) -->
  <ConsultationDialog
    bind:open={isConsultationOpen}
    appointment={selectedAppointmentForConsult}
    activeDoctor={activeDoctor}
    onComplete={() => {
      loadDoctorQueue(false);
    }}
  />

  <!-- Patient Chart History Modal -->
  <PatientChartDialog
    bind:open={isChartOpen}
    patient={selectedPatientForChart}
  />
</div>
