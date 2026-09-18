<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient, type Appointment, type ApiError } from "$lib/api";
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
    Loader2,
  } from "lucide-svelte";

  interface Props {
    isBookingModalOpen?: boolean;
    preselectedPatient?: Patient | null;
  }

  let {
    isBookingModalOpen = $bindable(false),
    preselectedPatient = null,
  }: Props = $props();

  // Patients for dropdown selection
  let patientList = $state<Patient[]>([]);

  // Appointments master collection
  let allAppointments = $state<Appointment[]>([]);
  let isLoading = $state(false);
  let errorMessage = $state<string | null>(null);
  let bannerNotice = $state<string | null>(null);

  // Filters
  type StatusFilter = "ALL" | "Scheduled" | "Completed" | "Cancelled";
  let activeFilter = $state<StatusFilter>("ALL");
  let searchQuery = $state("");

  // Pagination
  let pageSize = $state(10);
  let currentPage = $state(1);

  // Booking Modal State
  let selectedPatientId = $state<number | null>(null);
  let doctorName = $state("");
  let appDate = $state(new Date().toISOString().split("T")[0]);
  let isSubmitting = $state(false);
  let bookingErrors = $state<Record<string, string[]>>({});

  // Edit / Delete Dialog State
  let isEditDialogOpen = $state(false);
  let appointmentForEdit = $state<Appointment | null>(null);

  let isDeleteDialogOpen = $state(false);
  let appointmentForDelete = $state<Appointment | null>(null);

  async function loadInitialData() {
    isLoading = true;
    errorMessage = null;
    try {
      const [patients, appointments] = await Promise.all([
        api.listPatients(),
        api.listAllAppointments(),
      ]);
      patientList = patients;
      allAppointments = appointments;
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
    } finally {
      isLoading = false;
    }
  }

  // Filter count counters
  let countAll = $derived(allAppointments.length);
  let countScheduled = $derived(
    allAppointments.filter((a) => a.status === "Scheduled").length
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

  // Pagination Derivations & Clamping
  let totalPages = $derived(
    Math.max(1, Math.ceil(filteredAppointments.length / pageSize))
  );

  $effect(() => {
    if (currentPage > totalPages) {
      currentPage = totalPages;
    }
  });

  let paginatedAppointments = $derived.by(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAppointments.slice(start, start + pageSize);
  });

  let startRecord = $derived(
    filteredAppointments.length === 0 ? 0 : (currentPage - 1) * pageSize + 1
  );
  let endRecord = $derived(
    Math.min(currentPage * pageSize, filteredAppointments.length)
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

  function openBookingModal(patientId?: number) {
    if (patientId) {
      selectedPatientId = patientId;
    } else if (preselectedPatient) {
      selectedPatientId = preselectedPatient.id;
    } else if (patientList.length > 0) {
      selectedPatientId = patientList[0].id;
    }
    doctorName = "";
    appDate = new Date().toISOString().split("T")[0];
    bookingErrors = {};
    isBookingModalOpen = true;
  }

  async function handleCreateBooking(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedPatientId) {
      bookingErrors = { general: ["Please select a patient."] };
      return;
    }

    const trimmedDoctor = doctorName.trim();
    const localErrors: Record<string, string[]> = {};
    if (!trimmedDoctor) localErrors.doctor_name = ["Doctor name is required."];
    if (!appDate) localErrors.app_date = ["Appointment date is required."];

    if (Object.keys(localErrors).length > 0) {
      bookingErrors = localErrors;
      return;
    }

    isSubmitting = true;
    bookingErrors = {};

    try {
      const newApp = await api.bookAppointment({
        patient_id: selectedPatientId,
        doctor_name: trimmedDoctor,
        app_date: appDate,
      });

      isBookingModalOpen = false;
      bannerNotice = `Appointment #${newApp.id} booked with ${newApp.doctor_name} for ${newApp.app_date}.`;
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
    status: "Scheduled" | "Completed" | "Cancelled"
  ) {
    bannerNotice = null;
    try {
      const updated = await api.updateAppointmentStatus(appointmentId, status);
      bannerNotice = `Appointment #${updated.id} status updated to ${updated.status}.`;
      await reloadAppointments();
    } catch (err) {
      const e = err as ApiError;
      errorMessage = `Status update failed: ${e.message}`;
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
    }
  });

  onMount(() => {
    loadInitialData();
  });
</script>

<div class="flex flex-col gap-6">
  <!-- Banner Notice -->
  {#if bannerNotice}
    <div class="rounded-xl bg-emerald-50 border border-emerald-200/80 p-4 text-sm text-emerald-900 flex items-center justify-between shadow-sm">
      <div class="flex items-center gap-2">
        <CheckCircle2 class="size-5 text-emerald-600 shrink-0" />
        <span class="font-medium">{bannerNotice}</span>
      </div>
      <button onclick={() => (bannerNotice = null)} class="text-emerald-700 hover:text-emerald-900 text-xs font-semibold cursor-pointer">
        Dismiss
      </button>
    </div>
  {/if}

  <!-- Top Metrics Cards (Matching Reference Screenshot) -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <p class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Consultations</p>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{countAll}</p>
      <p class="text-[11px] text-muted-foreground mt-1">Master schedule count</p>
    </div>
    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <p class="text-xs font-medium text-sky-700 uppercase tracking-wider">Scheduled</p>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{countScheduled}</p>
      <p class="text-[11px] text-muted-foreground mt-1">Pending clinical visits</p>
    </div>
    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <p class="text-xs font-medium text-emerald-700 uppercase tracking-wider">Completed</p>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{countCompleted}</p>
      <p class="text-[11px] text-muted-foreground mt-1">Discharged records</p>
    </div>
    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <p class="text-xs font-medium text-zinc-600 uppercase tracking-wider">Cancelled</p>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{countCancelled}</p>
      <p class="text-[11px] text-muted-foreground mt-1">Deferred or withdrawn</p>
    </div>
  </div>

  <!-- Segmented Tabs & Toolbar Bar (Matching Reference Screenshot) -->
  <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
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
      <Tabs.List>
        <Tabs.Trigger value="ALL" class="min-w-[72px]">
          All <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countAll})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Scheduled" class="min-w-[110px]">
          Scheduled <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countScheduled})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Completed" class="min-w-[110px]">
          Completed <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countCompleted})</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="Cancelled" class="min-w-[104px]">
          Cancelled <span class="ml-1 text-[11px] tabular-nums text-muted-foreground font-normal">({countCancelled})</span>
        </Tabs.Trigger>
      </Tabs.List>
    </Tabs.Root>

    <!-- Search, Refresh, and Action -->
    <div class="flex items-center gap-2">
      <div class="relative w-full md:w-64">
        <Search class="absolute left-3 top-2.5 size-4 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          placeholder="Filter doctor, patient, ID..."
          value={searchQuery}
          oninput={handleSearchInput}
          class="pl-9 h-9"
        />
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
    <div class="rounded-xl bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive">
      {errorMessage}
    </div>
  {:else}
    <div class="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-20">Appt #</TableHead>
            <TableHead>Patient</TableHead>
            <TableHead>Doctor</TableHead>
            <TableHead class="w-32">Date</TableHead>
            <TableHead class="w-28 text-center">Status</TableHead>
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
          {:else if filteredAppointments.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-32 text-center text-sm text-muted-foreground">
                {searchQuery || activeFilter !== "ALL"
                  ? "No appointments match your active filter or search query."
                  : "No appointments have been booked yet. Click 'New Appointment' to schedule a consultation."}
              </TableCell>
            </TableRow>
          {:else}
            {#each paginatedAppointments as app (app.id)}
              <TableRow>
                <!-- Appt ID -->
                <TableCell class="font-mono text-xs text-muted-foreground">
                  #{app.id}
                </TableCell>

                <!-- Patient -->
                <TableCell class="font-medium text-foreground">
                  {app.patient_name}
                  <span class="text-xs text-muted-foreground ml-1 font-normal">(ID #{app.patient_id})</span>
                </TableCell>

                <!-- Doctor -->
                <TableCell class="text-foreground">
                  {app.doctor_name}
                </TableCell>

                <!-- Date -->
                <TableCell class="tabular-nums text-xs text-muted-foreground">
                  {app.app_date}
                </TableCell>

                <!-- Status Indicator Badge -->
                <TableCell class="text-center">
                  {#if app.status === "Scheduled"}
                    <span class="inline-flex items-center gap-1.5 text-xs text-sky-700 font-medium">
                      <Clock class="size-3.5 text-sky-600 shrink-0" />
                      Scheduled
                    </span>
                  {:else if app.status === "Completed"}
                    <span class="inline-flex items-center gap-1.5 text-xs text-emerald-700 font-medium">
                      <CheckCircle2 class="size-3.5 text-emerald-600 shrink-0" />
                      Completed
                    </span>
                  {:else if app.status === "Cancelled"}
                    <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
                      <XCircle class="size-3.5 text-muted-foreground shrink-0" />
                      Cancelled
                    </span>
                  {/if}
                </TableCell>

                <!-- Dropdown Menu Actions -->
                <TableCell class="text-right">
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger class="inline-flex items-center justify-center rounded-md size-8 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-ring">
                      <MoreHorizontal class="size-4" />
                      <span class="sr-only">Open menu</span>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Content align="end">
                      {#if app.status === "Scheduled"}
                        <DropdownMenu.Item
                          onclick={() => handleStatusChange(app.id, "Completed")}
                          class="text-emerald-700 focus:bg-emerald-50 focus:text-emerald-800 cursor-pointer"
                        >
                          <CheckCircle2 class="size-4 mr-2" />
                          <span>Mark Completed</span>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item
                          onclick={() => openEditAppointment(app)}
                          class="cursor-pointer"
                        >
                          <Calendar class="size-4 mr-2" />
                          <span>Reschedule / Edit</span>
                        </DropdownMenu.Item>
                        <DropdownMenu.Separator />
                        <DropdownMenu.Item
                          onclick={() => handleStatusChange(app.id, "Cancelled")}
                          class="text-amber-700 focus:bg-amber-50 focus:text-amber-800 cursor-pointer"
                        >
                          <XCircle class="size-4 mr-2" />
                          <span>Cancel Appointment</span>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item
                          onclick={() => openDeleteAppointment(app)}
                          class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                        >
                          <Trash2 class="size-4 mr-2" />
                          <span>Delete</span>
                        </DropdownMenu.Item>
                      {:else if app.status === "Cancelled"}
                        <DropdownMenu.Item
                          onclick={() => handleStatusChange(app.id, "Scheduled")}
                          class="text-sky-700 focus:bg-sky-50 focus:text-sky-800 cursor-pointer"
                        >
                          <RotateCcw class="size-4 mr-2" />
                          <span>Restore to Scheduled</span>
                        </DropdownMenu.Item>
                        <DropdownMenu.Separator />
                        <DropdownMenu.Item
                          onclick={() => openDeleteAppointment(app)}
                          class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                        >
                          <Trash2 class="size-4 mr-2" />
                          <span>Delete</span>
                        </DropdownMenu.Item>
                      {:else if app.status === "Completed"}
                        <!-- Completed records are immutable: only deletion is permissible -->
                        <DropdownMenu.Item
                          onclick={() => openDeleteAppointment(app)}
                          class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                        >
                          <Trash2 class="size-4 mr-2" />
                          <span>Delete</span>
                        </DropdownMenu.Item>
                      {/if}
                    </DropdownMenu.Content>
                  </DropdownMenu.Root>
                </TableCell>
              </TableRow>
            {/each}
          {/if}
        </TableBody>
      </Table>

      <!-- Integrated Table Footer Pagination (Matching Reference Screenshot) -->
      <div class="border-t border-border px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground bg-muted/20">
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
        <!-- Patient Selector -->
        <div>
          <label for="modalPatientSelect" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Patient <span class="text-destructive">*</span>
          </label>
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
        </div>

        <!-- Doctor Name -->
        <div>
          <label for="modalDoctor" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Attending Doctor <span class="text-destructive">*</span>
          </label>
          <Input
            id="modalDoctor"
            type="text"
            placeholder="e.g. Dr. Maria Cruz"
            bind:value={doctorName}
            aria-invalid={!!bookingErrors.doctor_name}
            disabled={isSubmitting}
            autofocus
          />
          {#if bookingErrors.doctor_name}
            <p class="text-xs text-destructive mt-1">{bookingErrors.doctor_name.join(" ")}</p>
          {/if}
        </div>

        <!-- Date -->
        <div>
          <label for="modalDate" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Consultation Date <span class="text-destructive">*</span>
          </label>
          <Input
            id="modalDate"
            type="date"
            bind:value={appDate}
            aria-invalid={!!bookingErrors.app_date}
            disabled={isSubmitting}
          />
          {#if bookingErrors.app_date}
            <p class="text-xs text-destructive mt-1">{bookingErrors.app_date.join(" ")}</p>
          {/if}
        </div>

        {#if bookingErrors.general}
          <div class="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
            {bookingErrors.general.join(" ")}
          </div>
        {/if}

        <Dialog.Footer class="pt-2">
          <Button
            type="button"
            variant="outline"
            onclick={() => (isBookingModalOpen = false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="size-4 animate-spin" />
            {/if}
            Confirm Schedule
          </Button>
        </Dialog.Footer>
      </form>
    </Dialog.Content>
  </Dialog.Root>

  <!-- Edit Appointment Dialog -->
  <EditAppointmentDialog
    bind:open={isEditDialogOpen}
    appointment={appointmentForEdit}
    onSuccess={() => {
      bannerNotice = `Appointment #${appointmentForEdit?.id} rescheduled successfully.`;
      reloadAppointments();
    }}
  />

  <!-- Delete Appointment Dialog -->
  <DeleteAppointmentDialog
    bind:open={isDeleteDialogOpen}
    appointment={appointmentForDelete}
    onSuccess={() => {
      bannerNotice = `Appointment #${appointmentForDelete?.id} deleted successfully.`;
      reloadAppointments();
    }}
  />
</div>
