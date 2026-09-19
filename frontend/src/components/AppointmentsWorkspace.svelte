<script lang="ts">
  import { onMount } from "svelte";
  import {
    api,
    type Patient,
    type Appointment,
    type StaffUser,
    type AppointmentStatus,
    type ApiError,
  } from "$lib/api";
  import { toast } from "$lib/toast.svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import {
    Table,
    TableHeader,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
  } from "$lib/components/ui/table";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu";
  import * as Dialog from "$lib/components/ui/dialog";
  import * as Tabs from "$lib/components/ui/tabs";
  import EditAppointmentDialog from "./EditAppointmentDialog.svelte";
  import DeleteAppointmentDialog from "./DeleteAppointmentDialog.svelte";
  import {
    CalendarPlus,
    Search,
    RefreshCw,
    MoreHorizontal,
    CheckCircle2,
    Clock,
    XCircle,
    RotateCcw,
    Calendar,
    Trash2,
    ChevronLeft,
    ChevronRight,
    ChevronsLeft,
    ChevronsRight,
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    X,
    Loader2,
    AlertTriangle,
    UserCheck,
    Stethoscope,
    Activity,
  } from "lucide-svelte";

  interface Props {
    isBookingModalOpen?: boolean;
    preselectedPatient?: Patient | null;
    onClearPreselectedPatient?: () => void;
  }

  let {
    isBookingModalOpen = $bindable(false),
    preselectedPatient = null,
    onClearPreselectedPatient,
  }: Props = $props();

  // Patients & Doctors for dropdown selection
  let patientList = $state<Patient[]>([]);
  let doctorList = $state<StaffUser[]>([]);

  // Appointments master collection
  let allAppointments = $state<Appointment[]>([]);
  let isLoading = $state(false);
  let errorMessage = $state<string | null>(null);

  // Filters (5-State Clinical Lifecycle + ALL)
  type StatusFilter =
    | "ALL"
    | "Checked In"
    | "Scheduled"
    | "In Consultation"
    | "Completed"
    | "Cancelled";
  let activeFilter = $state<StatusFilter>("ALL");
  let searchQuery = $state("");

  // Sorting state (default: chronological appointment date)
  type AppointmentSortField = "id" | "patient_name" | "doctor_name" | "app_date" | "status";
  let sortField = $state<AppointmentSortField>("app_date");
  let sortDirection = $state<"asc" | "desc">("asc");

  // Pagination
  let pageSize = $state(10);
  let currentPage = $state(1);

  // Booking Modal State
  let selectedPatientId = $state<number | null>(null);
  let selectedDoctorId = $state<number | null>(null);
  let doctorName = $state("");
  let appDate = $state(new Date().toISOString().split("T")[0]);
  let appTime = $state("09:00");
  let reasonForVisit = $state("");
  let conflictWarning = $state<string | null>(null);
  let isCheckingConflict = $state(false);
  let overrideConflict = $state(false);
  let conflictCheckTimer: ReturnType<typeof setTimeout> | null = null;
  let isSubmitting = $state(false);
  let bookingErrors = $state<Record<string, string[]>>({});

  // Edit / Delete Dialog State
  let isEditDialogOpen = $state(false);
  let appointmentForEdit = $state<Appointment | null>(null);

  let isDeleteDialogOpen = $state(false);
  let appointmentForDelete = $state<Appointment | null>(null);

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

  async function loadInitialData() {
    isLoading = true;
    errorMessage = null;
    try {
      const [patients, appointments, doctors] = await Promise.all([
        api.listPatients(),
        api.listAllAppointments(),
        api.auth.listDoctors(),
      ]);
      patientList = patients;
      allAppointments = appointments;
      doctorList = doctors;
    } catch (err) {
      const e = err as ApiError;
      errorMessage = e.message || "Failed to load clinic records.";
    } finally {
      isLoading = false;
    }
  }

  async function reloadAppointments() {
    isLoading = true;
    try {
      allAppointments = await api.listAllAppointments();
    } catch (err) {
      const e = err as ApiError;
      errorMessage = e.message || "Failed to refresh appointments.";
      toast.error(errorMessage);
    } finally {
      isLoading = false;
    }
  }

  // Filter count counters
  let countAll = $derived(allAppointments.length);
  let countCheckedIn = $derived(
    allAppointments.filter((a) => a.status === "Checked In").length
  );
  let countScheduled = $derived(
    allAppointments.filter((a) => a.status === "Scheduled").length
  );
  let countInConsultation = $derived(
    allAppointments.filter((a) => a.status === "In Consultation").length
  );
  let countCompleted = $derived(
    allAppointments.filter((a) => a.status === "Completed").length
  );
  let countCancelled = $derived(
    allAppointments.filter((a) => a.status === "Cancelled").length
  );

  // Filtered appointments
  let filteredAppointments = $derived.by(() => {
    let list = allAppointments;

    if (activeFilter !== "ALL") {
      list = list.filter((app) => app.status === activeFilter);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (app) =>
          app.patient_name.toLowerCase().includes(q) ||
          app.doctor_name.toLowerCase().includes(q) ||
          String(app.id).includes(q) ||
          String(app.patient_id).includes(q)
      );
    }

    return list;
  });

  // Sorting derivation
  let sortedAppointments = $derived.by(() => {
    const list = [...filteredAppointments];
    return list.sort((a, b) => {
      let cmp = 0;
      if (sortField === "id") {
        cmp = a.id - b.id;
      } else if (sortField === "patient_name") {
        cmp = a.patient_name.localeCompare(b.patient_name);
      } else if (sortField === "doctor_name") {
        cmp = a.doctor_name.localeCompare(b.doctor_name);
      } else if (sortField === "app_date") {
        cmp = a.app_date.localeCompare(b.app_date);
      } else if (sortField === "status") {
        cmp = a.status.localeCompare(b.status);
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });
  });

  function toggleSort(field: AppointmentSortField) {
    if (sortField === field) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDirection = field === "app_date" || field === "patient_name" || field === "doctor_name" ? "asc" : "desc";
    }
    currentPage = 1;
  }

  // Pagination Derivations & Clamping
  let totalPages = $derived(
    Math.max(1, Math.ceil(sortedAppointments.length / pageSize))
  );

  $effect(() => {
    if (currentPage > totalPages) {
      currentPage = totalPages;
    }
  });

  let paginatedAppointments = $derived.by(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedAppointments.slice(start, start + pageSize);
  });

  let startRecord = $derived(
    sortedAppointments.length === 0 ? 0 : (currentPage - 1) * pageSize + 1
  );
  let endRecord = $derived(
    Math.min(currentPage * pageSize, sortedAppointments.length)
  );

  function handleFilterChange(filter: StatusFilter) {
    activeFilter = filter;
    currentPage = 1;
  }

  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement;
    searchQuery = target.value;
    currentPage = 1;
  }

  function clearSearch() {
    searchQuery = "";
    currentPage = 1;
  }

  function setQuickDate(daysOffset: number) {
    const d = new Date();
    d.setDate(d.getDate() + daysOffset);
    appDate = d.toISOString().split("T")[0];
  }

  function runConflictCheck() {
    if (conflictCheckTimer) clearTimeout(conflictCheckTimer);
    conflictWarning = null;
    if (!selectedDoctorId || selectedDoctorId <= 0 || !appDate || !appTime) {
      isCheckingConflict = false;
      return;
    }

    isCheckingConflict = true;
    conflictCheckTimer = setTimeout(async () => {
      try {
        if (!selectedDoctorId || selectedDoctorId <= 0) return;
        const res = await api.clinical.checkScheduleConflict(
          selectedDoctorId,
          appDate,
          appTime
        );
        if (res.has_conflict && res.conflicts.length > 0) {
          const first = res.conflicts[0];
          const doc = doctorList.find((d) => d.id === selectedDoctorId);
          const docDisplayName = doc ? doc.full_name : doctorName || "Doctor";
          const formattedConflictTime = formatTime(first.app_time);
          conflictWarning = `${docDisplayName} already has an appointment scheduled (#${first.id} with ${first.patient_name} at ${formattedConflictTime}) within the +/- 15 minute window.`;
        } else {
          conflictWarning = null;
          overrideConflict = false;
        }
      } catch {
        // Non-blocking conflict check failure
      } finally {
        isCheckingConflict = false;
      }
    }, 250);
  }

  $effect(() => {
    if (isBookingModalOpen && selectedDoctorId && appDate && appTime) {
      runConflictCheck();
    }
  });

  function openBookingModal(patientId?: number) {
    if (patientId) {
      selectedPatientId = patientId;
    } else if (preselectedPatient) {
      selectedPatientId = preselectedPatient.id;
    } else if (patientList.length > 0) {
      selectedPatientId = patientList[0].id;
    }
    selectedDoctorId = doctorList.length > 0 ? doctorList[0].id : null;
    doctorName = doctorList.length > 0 ? doctorList[0].full_name : "";
    appDate = new Date().toISOString().split("T")[0];
    appTime = "09:00";
    reasonForVisit = "";
    conflictWarning = null;
    overrideConflict = false;
    bookingErrors = {};
    isBookingModalOpen = true;
  }

  async function handleCreateBooking(
    e: Event,
    initialStatus: AppointmentStatus = "Scheduled"
  ) {
    e.preventDefault();
    if (!selectedPatientId) {
      bookingErrors = { general: ["Please select a patient."] };
      return;
    }

    const trimmedDoctor = doctorName.trim();
    const localErrors: Record<string, string[]> = {};
    if (!trimmedDoctor && (!selectedDoctorId || selectedDoctorId <= 0)) {
      localErrors.doctor_name = ["Doctor selection or doctor name is required."];
    }
    if (!appDate) localErrors.app_date = ["Appointment date is required."];
    if (!appTime) localErrors.app_time = ["Appointment time is required."];

    if (conflictWarning && !overrideConflict) {
      localErrors.general = [
        "A schedule conflict was detected. Check 'Emergency / Walk-in Override' to proceed.",
      ];
    }

    if (Object.keys(localErrors).length > 0) {
      bookingErrors = localErrors;
      return;
    }

    isSubmitting = true;
    bookingErrors = {};

    try {
      const newApp = await api.bookAppointment({
        patient_id: selectedPatientId,
        doctor_name:
          trimmedDoctor ||
          (doctorList.find((d) => d.id === selectedDoctorId)?.full_name ??
            "Attending Physician"),
        doctor_id: selectedDoctorId && selectedDoctorId > 0 ? selectedDoctorId : null,
        app_date: appDate,
        app_time: appTime,
        reason_for_visit: reasonForVisit.trim(),
        initial_status: initialStatus,
      });

      isBookingModalOpen = false;
      const statusNote =
        newApp.status === "Checked In" ? " (Checked in to Waiting Room)" : "";
      toast.success(
        `Appointment #${newApp.id} booked with ${newApp.doctor_name} for ${newApp.app_date} at ${formatTime(newApp.app_time)}${statusNote}.`
      );
      await reloadAppointments();
    } catch (err) {
      const e = err as ApiError;
      bookingErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }

  async function handleStatusChange(
    appointmentId: number,
    status: AppointmentStatus
  ) {
    try {
      const updated = await api.updateAppointmentStatus(appointmentId, status);
      toast.success(`Appointment #${updated.id} marked as ${updated.status}.`);
      await reloadAppointments();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`Status update failed: ${e.message}`);
    }
  }

  function openEditAppointment(app: Appointment) {
    appointmentForEdit = app;
    isEditDialogOpen = true;
  }

  function openDeleteAppointment(app: Appointment) {
    appointmentForDelete = app;
    isDeleteDialogOpen = true;
  }

  $effect(() => {
    if (preselectedPatient) {
      selectedPatientId = preselectedPatient.id;
      openBookingModal(preselectedPatient.id);
      onClearPreselectedPatient?.();
    }
  });

  onMount(() => {
    loadInitialData();
  });
</script>

<div class="flex flex-col gap-4 flex-1 min-h-0 overflow-hidden">
  <!-- Top Metrics Cards (5-State Clinical Lifecycle) -->
  <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 shrink-0">
    <div class="rounded-xl border bg-card text-card-foreground p-3.5 sm:p-4 shadow-sm">
      <p class="text-[11px] sm:text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Visits</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{countAll}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Master schedule count</p>
    </div>
    <div class="rounded-xl border border-amber-500/30 bg-amber-500/5 text-card-foreground p-3.5 sm:p-4 shadow-sm">
      <p class="text-[11px] sm:text-xs font-semibold text-amber-700 uppercase tracking-wider">Waiting Room</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{countCheckedIn}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Checked in at clinic</p>
    </div>
    <div class="rounded-xl border bg-card text-card-foreground p-3.5 sm:p-4 shadow-sm">
      <p class="text-[11px] sm:text-xs font-medium text-muted-foreground uppercase tracking-wider">Scheduled</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{countScheduled}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Pending clinical visits</p>
    </div>
    <div class="rounded-xl border border-primary/30 bg-primary/5 text-card-foreground p-3.5 sm:p-4 shadow-sm">
      <p class="text-[11px] sm:text-xs font-semibold text-primary uppercase tracking-wider">Consulting</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{countInConsultation}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Currently with physician</p>
    </div>
    <div class="rounded-xl border bg-card text-card-foreground p-3.5 sm:p-4 shadow-sm">
      <p class="text-[11px] sm:text-xs font-medium text-muted-foreground uppercase tracking-wider">Completed</p>
      <p class="text-xl sm:text-2xl font-bold tracking-tight text-foreground mt-1.5">{countCompleted}</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">Discharged records</p>
    </div>
  </div>

  <!-- Segmented Tabs & Toolbar Bar -->
  <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shrink-0">
    <!-- Status Filter Tabs -->
    <Tabs.Root
      value={activeFilter}
      onValueChange={(val) => {
        if (val) {
          activeFilter = val as StatusFilter;
          currentPage = 1;
        }
      }}
    >
      <Tabs.List class="flex flex-wrap h-auto p-1">
        <Tabs.Trigger value="ALL" class="min-w-[64px]">
          All <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countAll})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Checked In" class="min-w-[110px]">
          Waiting Room <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countCheckedIn})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Scheduled" class="min-w-[95px]">
          Scheduled <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countScheduled})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="In Consultation" class="min-w-[110px]">
          Consulting <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countInConsultation})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Completed" class="min-w-[95px]">
          Completed <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countCompleted})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Cancelled" class="min-w-[90px]">
          Cancelled <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countCancelled})</span>
        </Tabs.Trigger>
      </Tabs.List>
    </Tabs.Root>

    <!-- Search, Refresh, and Action -->
    <div class="flex items-center gap-2">
      {#if totalPages > 1}
        <div class="hidden sm:flex items-center gap-1.5 mr-1 text-xs text-muted-foreground border-r border-border pr-2.5">
          <span class="font-medium text-foreground tabular-nums">
            {currentPage}/{totalPages}
          </span>
          <Button
            type="button"
            variant="outline"
            size="icon"
            class="size-7 cursor-pointer"
            onclick={() => (currentPage = Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            title="Previous Page"
          >
            <ChevronLeft class="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            class="size-7 cursor-pointer"
            onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            title="Next Page"
          >
            <ChevronRight class="size-3.5" />
          </Button>
        </div>
      {/if}

      <div class="relative w-full md:w-64">
        <Search class="absolute left-3 top-2.5 size-4 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          placeholder="Filter doctor, patient, ID..."
          value={searchQuery}
          oninput={handleSearchInput}
          onkeydown={(e) => {
            if (e.key === "Escape") clearSearch();
          }}
          data-search-input="true"
          class="pl-9 pr-8 h-9"
        />
        {#if searchQuery}
          <button
            type="button"
            onclick={clearSearch}
            class="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground cursor-pointer"
            title="Clear filter (Esc)"
          >
            <X class="size-4" />
          </button>
        {/if}
      </div>
      <Button
        variant="outline"
        size="sm"
        class="h-9 px-3 cursor-pointer"
        onclick={reloadAppointments}
        disabled={isLoading}
      >
        {#if isLoading}
          <Loader2 class="size-3.5 animate-spin" />
        {:else}
          <RefreshCw class="size-3.5" />
        {/if}
        <span class="sr-only">Refresh</span>
      </Button>
      <Button onclick={() => openBookingModal()} size="sm" class="h-9 px-3 cursor-pointer">
        <CalendarPlus class="size-3.5 mr-1.5" />
        <span>New Appointment</span>
      </Button>
    </div>
  </div>

  <!-- Appointments Table View (Matching Reference Screenshot) -->
  {#if errorMessage}
    <div class="rounded-xl bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive shrink-0">
      {errorMessage}
    </div>
  {:else}
    <div class="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col flex-1 min-h-0">
      <Table containerClass="flex-1 min-h-0 overflow-y-auto">
        <TableHeader class="sticky top-0 bg-card z-10 shadow-xs border-b [&_tr]:bg-card">
          <TableRow>
            <TableHead class="w-24">
              <button
                type="button"
                onclick={() => toggleSort("id")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Appt #
                {#if sortField === "id"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead>
              <button
                type="button"
                onclick={() => toggleSort("patient_name")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Patient
                {#if sortField === "patient_name"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead>
              <button
                type="button"
                onclick={() => toggleSort("doctor_name")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Doctor
                {#if sortField === "doctor_name"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead class="w-36">
              <button
                type="button"
                onclick={() => toggleSort("app_date")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Date
                {#if sortField === "app_date"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead class="w-32 text-center">
              <button
                type="button"
                onclick={() => toggleSort("status")}
                class="inline-flex items-center justify-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs w-full"
              >
                Status
                {#if sortField === "status"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead class="w-16 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {#if isLoading && allAppointments.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-32 text-center text-sm text-muted-foreground">
                <div class="flex items-center justify-center gap-2">
                  <RefreshCw class="animate-spin size-4 text-primary" />
                  <span>Loading consultation schedules...</span>
                </div>
              </TableCell>
            </TableRow>
          {:else if sortedAppointments.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-36 text-center text-sm text-muted-foreground">
                {#if searchQuery || activeFilter !== "ALL"}
                  <div class="flex flex-col items-center justify-center gap-2 py-2">
                    <p>No appointments match your active filter or search query.</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onclick={() => {
                        searchQuery = "";
                        activeFilter = "ALL";
                        currentPage = 1;
                      }}
                      class="cursor-pointer"
                    >
                      Reset All Filters
                    </Button>
                  </div>
                {:else}
                  No appointments have been booked yet. Click 'New Appointment' to schedule a consultation.
                {/if}
              </TableCell>
            </TableRow>
          {:else}
            {#each paginatedAppointments as app (app.id)}
              <TableRow>
                <!-- Appt ID -->
                <TableCell class="font-mono text-xs text-muted-foreground">
                  <Badge variant="outline" class="font-mono text-xs font-normal">
                    #{app.id}
                  </Badge>
                </TableCell>

                <!-- Patient -->
                <TableCell>
                  <div class="flex flex-col">
                    <span class="font-medium text-foreground">
                      {app.patient_name}
                      <span class="text-xs text-muted-foreground ml-1 font-normal">(ID #{app.patient_id})</span>
                    </span>
                    {#if app.reason_for_visit}
                      <span class="text-[11px] text-muted-foreground line-clamp-1 italic">
                        Reason: {app.reason_for_visit}
                      </span>
                    {/if}
                  </div>
                </TableCell>

                <!-- Doctor -->
                <TableCell class="text-foreground">
                  {app.doctor_name}
                </TableCell>

                <!-- Schedule Date & Time -->
                <TableCell>
                  <div class="flex flex-col">
                    <span class="text-xs font-medium text-foreground">{app.app_date}</span>
                    <span class="text-[11px] text-muted-foreground font-mono flex items-center gap-1">
                      <Clock class="size-3 text-muted-foreground shrink-0" />
                      {formatTime(app.app_time)}
                    </span>
                  </div>
                </TableCell>

                <!-- Status Indicator Badge (5 Clinical States) -->
                <TableCell class="text-center">
                  {#if app.status === "Scheduled"}
                    <Badge variant="outline" class="gap-1 font-medium text-xs text-muted-foreground">
                      <Clock class="size-3 shrink-0" />
                      Scheduled
                    </Badge>
                  {:else if app.status === "Checked In"}
                    <Badge variant="secondary" class="gap-1 font-medium text-xs">
                      <UserCheck class="size-3 shrink-0" />
                      Checked In
                    </Badge>
                  {:else if app.status === "In Consultation"}
                    <Badge variant="default" class="gap-1 font-medium text-xs">
                      <Stethoscope class="size-3 shrink-0" />
                      Consulting
                    </Badge>
                  {:else if app.status === "Completed"}
                    <Badge variant="outline" class="gap-1 font-medium text-xs">
                      <CheckCircle2 class="size-3 shrink-0" />
                      Completed
                    </Badge>
                  {:else if app.status === "Cancelled"}
                    <Badge variant="outline" class="gap-1 font-medium text-xs opacity-70">
                      <XCircle class="size-3 shrink-0" />
                      Cancelled
                    </Badge>
                  {/if}
                </TableCell>

                <!-- Actions: Quick Check In + Dropdown Menu -->
                <TableCell class="text-right">
                  <div class="inline-flex items-center justify-end gap-1.5">
                    {#if app.status === "Scheduled"}
                      <Button
                        size="sm"
                        variant="secondary"
                        class="h-7 text-xs px-2 cursor-pointer inline-flex items-center gap-1 font-medium"
                        onclick={() => handleStatusChange(app.id, "Checked In")}
                        title="Check in patient to Waiting Room"
                      >
                        <UserCheck class="size-3" />
                        Check In
                      </Button>
                    {/if}

                    <DropdownMenu.Root>
                      <DropdownMenu.Trigger class="inline-flex items-center justify-center rounded-md size-8 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        <MoreHorizontal class="size-4" />
                        <span class="sr-only">Open menu</span>
                      </DropdownMenu.Trigger>
                      <DropdownMenu.Content align="end">
                        {#if app.status === "Scheduled"}
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Checked In")}
                            class="text-amber-800 focus:bg-amber-50 focus:text-amber-900 cursor-pointer"
                          >
                            <UserCheck class="size-4 mr-2" />
                            <span>Check In (Waiting Room)</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            onclick={() => openEditAppointment(app)}
                            class="cursor-pointer"
                          >
                            <Calendar class="size-4 mr-2" />
                            <span>Reschedule Visit</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Cancelled")}
                            class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                          >
                            <XCircle class="size-4 mr-2" />
                            <span>Cancel Appointment</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Separator />
                          <DropdownMenu.Item
                            onclick={() => openDeleteAppointment(app)}
                            class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                          >
                            <Trash2 class="size-4 mr-2" />
                            <span>Delete Record</span>
                          </DropdownMenu.Item>
                        {:else if app.status === "Checked In"}
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "In Consultation")}
                            class="text-purple-800 focus:bg-purple-50 focus:text-purple-900 cursor-pointer"
                          >
                            <Stethoscope class="size-4 mr-2" />
                            <span>Send to Consultation</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Scheduled")}
                            class="cursor-pointer"
                          >
                            <RotateCcw class="size-4 mr-2" />
                            <span>Return to Scheduled</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Cancelled")}
                            class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                          >
                            <XCircle class="size-4 mr-2" />
                            <span>Cancel Appointment</span>
                          </DropdownMenu.Item>
                        {:else if app.status === "In Consultation"}
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Completed")}
                            class="text-emerald-700 focus:bg-emerald-50 focus:text-emerald-800 cursor-pointer"
                          >
                            <CheckCircle2 class="size-4 mr-2" />
                            <span>Mark Completed</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Cancelled")}
                            class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                          >
                            <XCircle class="size-4 mr-2" />
                            <span>Cancel Appointment</span>
                          </DropdownMenu.Item>
                        {:else if app.status === "Completed"}
                          <div class="px-2 py-1.5 text-xs text-muted-foreground italic">
                            Finalized clinical visit
                          </div>
                        {:else if app.status === "Cancelled"}
                          <DropdownMenu.Item
                            onclick={() => handleStatusChange(app.id, "Scheduled")}
                            class="text-sky-700 focus:bg-sky-50 focus:text-sky-800 cursor-pointer"
                          >
                            <RotateCcw class="size-4 mr-2" />
                            <span>Reopen as Scheduled</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Separator />
                          <DropdownMenu.Item
                            onclick={() => openDeleteAppointment(app)}
                            class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                          >
                            <Trash2 class="size-4 mr-2" />
                            <span>Delete Record</span>
                          </DropdownMenu.Item>
                        {/if}
                      </DropdownMenu.Content>
                    </DropdownMenu.Root>
                  </div>
                </TableCell>
              </TableRow>
            {/each}
          {/if}
        </TableBody>
      </Table>

      <!-- Integrated Table Footer Pagination (Matching Reference Screenshot) -->
      <div class="border-t border-border px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground bg-muted/20 shrink-0">
        <div class="flex items-center gap-2">
          <span>Rows per page</span>
          <select
            class="h-8 rounded-md border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
            bind:value={pageSize}
            onchange={() => (currentPage = 1)}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <span class="ml-2">
            Showing {startRecord} to {endRecord} of {filteredAppointments.length} record(s)
          </span>
        </div>

        <div class="flex items-center gap-4">
          <span class="font-medium text-foreground">
            Page {currentPage} of {totalPages}
          </span>
          <div class="inline-flex items-center gap-1">
            <button
              class="p-1 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              onclick={() => (currentPage = 1)}
              disabled={currentPage === 1}
              title="First Page"
            >
              <ChevronsLeft class="size-4" />
            </button>
            <button
              class="p-1 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              onclick={() => (currentPage = Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              title="Previous Page"
            >
              <ChevronLeft class="size-4" />
            </button>
            <button
              class="p-1 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
              disabled={currentPage >= totalPages}
              title="Next Page"
            >
              <ChevronRight class="size-4" />
            </button>
            <button
              class="p-1 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              onclick={() => (currentPage = totalPages)}
              disabled={currentPage >= totalPages}
              title="Last Page"
            >
              <ChevronsRight class="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Modal Dialog: New Appointment -->
  <Dialog.Root bind:open={isBookingModalOpen}>
    <Dialog.Content class="sm:max-w-md">
      <Dialog.Header>
        <Dialog.Title>Schedule Consultation</Dialog.Title>
        <Dialog.Description>
          Select a registered patient, consultation date, and attending physician.
        </Dialog.Description>
      </Dialog.Header>

      <form onsubmit={handleCreateBooking} class="flex flex-col gap-4 py-2">
        <!-- Patient Selector with Empty State Guard -->
        <div>
          <label for="modalPatientSelect" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Patient <span class="text-destructive">*</span>
          </label>
          {#if patientList.length === 0}
            <div class="rounded-lg border border-amber-200/80 bg-amber-50/70 p-3 text-xs text-amber-900 flex flex-col gap-1.5">
              <p class="font-semibold">No Registered Patients</p>
              <p>You must register a patient record before scheduling an appointment.</p>
            </div>
          {:else}
            <select
              id="modalPatientSelect"
              class="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm w-full focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
              bind:value={selectedPatientId}
              disabled={isSubmitting}
            >
              {#each patientList as p (p.id)}
                <option value={p.id}>
                  #{p.id} &bull; {p.full_name} (Age {p.age})
                </option>
              {/each}
            </select>
          {/if}
        </div>

        <!-- Attending Physician Selector -->
        <div>
          <label for="modalDoctorSelect" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Attending Physician <span class="text-destructive">*</span>
          </label>
          <select
            id="modalDoctorSelect"
            class="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm w-full focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
            bind:value={selectedDoctorId}
            onchange={(e) => {
              const val = Number((e.target as HTMLSelectElement).value);
              selectedDoctorId = val > 0 ? val : null;
              if (val > 0) {
                const doc = doctorList.find((d) => d.id === val);
                if (doc) doctorName = doc.full_name;
              } else if (val === -1) {
                doctorName = "";
              }
            }}
            disabled={isSubmitting}
          >
            {#if doctorList.length > 0}
              <option value={null}>-- Select Attending Physician --</option>
              {#each doctorList as doc (doc.id)}
                <option value={doc.id}>
                  Dr. {doc.full_name.replace(/^Dr\.\s*/i, "")} ({doc.specialty || "General Medicine"})
                </option>
              {/each}
              <option value={-1}>Other / Visiting Physician...</option>
            {:else}
              <option value={null}>No registered physicians found</option>
              <option value={-1}>Custom Physician Name...</option>
            {/if}
          </select>

          {#if selectedDoctorId === -1 || doctorList.length === 0}
            <div class="mt-2">
              <Input
                id="modalCustomDoctor"
                type="text"
                placeholder="e.g. Dr. Maria Cruz"
                bind:value={doctorName}
                aria-invalid={!!bookingErrors.doctor_name}
                disabled={isSubmitting}
              />
            </div>
          {/if}

          {#if bookingErrors.doctor_name}
            <p class="text-xs text-destructive mt-1">{bookingErrors.doctor_name.join(" ")}</p>
          {/if}
        </div>

        <!-- Date & Time Row -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <!-- Date with Quick Chips -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="modalDate" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Date <span class="text-destructive">*</span>
              </label>
              <div class="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  class="h-6 text-[11px] px-1 text-muted-foreground hover:text-foreground cursor-pointer"
                  onclick={() => setQuickDate(0)}
                >
                  Today
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  class="h-6 text-[11px] px-1 text-muted-foreground hover:text-foreground cursor-pointer"
                  onclick={() => setQuickDate(1)}
                >
                  Tomorrow
                </Button>
              </div>
            </div>
            <Input
              id="modalDate"
              type="date"
              bind:value={appDate}
              aria-invalid={!!bookingErrors.app_date}
              disabled={isSubmitting || patientList.length === 0}
            />
            {#if bookingErrors.app_date}
              <p class="text-xs text-destructive mt-1">{bookingErrors.app_date.join(" ")}</p>
            {/if}
          </div>

          <!-- Time Slot -->
          <div>
            <label for="modalTime" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
              Time Slot <span class="text-destructive">*</span>
            </label>
            <Input
              id="modalTime"
              type="time"
              bind:value={appTime}
              aria-invalid={!!bookingErrors.app_time}
              disabled={isSubmitting || patientList.length === 0}
            />
            {#if bookingErrors.app_time}
              <p class="text-xs text-destructive mt-1">{bookingErrors.app_time.join(" ")}</p>
            {/if}
          </div>
        </div>

        <!-- Reason for Visit & Quick Chips -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label for="modalReason" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Reason for Visit
            </label>
            <div class="flex items-center gap-1 flex-wrap">
              {#each ["Checkup", "Follow-up", "Fever", "Rx Refill"] as reasonChip}
                <button
                  type="button"
                  class="text-[10px] bg-muted/70 hover:bg-muted text-muted-foreground hover:text-foreground px-1.5 py-0.5 rounded cursor-pointer transition-colors"
                  onclick={() => (reasonForVisit = reasonChip)}
                >
                  {reasonChip}
                </button>
              {/each}
            </div>
          </div>
          <Input
            id="modalReason"
            type="text"
            placeholder="e.g. Routine checkup, throat pain, prescription renewal"
            bind:value={reasonForVisit}
            disabled={isSubmitting || patientList.length === 0}
          />
        </div>

        <!-- Reactive Conflict Check Warning Banner -->
        {#if isCheckingConflict}
          <div class="flex items-center gap-2 text-xs text-muted-foreground py-1">
            <Loader2 class="size-3 animate-spin text-primary" />
            <span>Checking doctor schedule availability...</span>
          </div>
        {:else if conflictWarning}
          <div class="rounded-lg border border-amber-300 bg-amber-50/90 p-3 text-xs text-amber-900 flex flex-col gap-2">
            <div class="flex items-center gap-2 font-semibold text-amber-800">
              <AlertTriangle class="size-4 text-amber-600 shrink-0" />
              <span>Schedule Conflict Warning</span>
            </div>
            <p>{conflictWarning}</p>
            <label class="flex items-center gap-2 font-medium cursor-pointer text-amber-950 mt-1 select-none">
              <input
                type="checkbox"
                bind:checked={overrideConflict}
                class="rounded border-amber-400 text-amber-600 focus:ring-amber-500 cursor-pointer"
              />
              <span>Emergency / Walk-in Override (Book Anyway)</span>
            </label>
          </div>
        {/if}

        {#if bookingErrors.general}
          <div class="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
            {bookingErrors.general.join(" ")}
          </div>
        {/if}

        <Dialog.Footer class="pt-2 flex flex-col sm:flex-row gap-2">
          <Button
            type="button"
            variant="outline"
            onclick={() => (isBookingModalOpen = false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="secondary"
            onclick={(e) => handleCreateBooking(e, "Checked In")}
            disabled={isSubmitting || patientList.length === 0 || (!!conflictWarning && !overrideConflict)}
            class="cursor-pointer"
          >
            {#if isSubmitting}
              <Loader2 class="size-4 animate-spin mr-1" />
            {:else}
              <UserCheck class="size-4 mr-1" />
            {/if}
            Book & Check In
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting || patientList.length === 0 || (!!conflictWarning && !overrideConflict)}
            class="cursor-pointer"
          >
            {#if isSubmitting}
              <Loader2 class="size-4 animate-spin mr-1" />
            {/if}
            Book Appointment
          </Button>
        </Dialog.Footer>
      </form>
    </Dialog.Content>
  </Dialog.Root>

  <!-- Edit Appointment Dialog -->
  <EditAppointmentDialog
    bind:open={isEditDialogOpen}
    appointment={appointmentForEdit}
    doctorList={doctorList}
    onSuccess={() => {
      toast.success(`Appointment #${appointmentForEdit?.id} updated.`);
      reloadAppointments();
    }}
  />

  <!-- Delete Appointment Dialog -->
  <DeleteAppointmentDialog
    bind:open={isDeleteDialogOpen}
    appointment={appointmentForDelete}
    onSuccess={() => {
      toast.success(`Appointment #${appointmentForDelete?.id} deleted.`);
      reloadAppointments();
    }}
  />
</div>
