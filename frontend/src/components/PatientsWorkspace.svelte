<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient, type ApiError } from "$lib/api";
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
  import EditPatientDialog from "./EditPatientDialog.svelte";
  import DeletePatientDialog from "./DeletePatientDialog.svelte";
  import {
    UserPlus,
    Search,
    RefreshCw,
    MoreHorizontal,
    CalendarPlus,
    Pencil,
    Trash2,
    Users,
    CalendarCheck,
    ClipboardList,
    ChevronLeft,
    ChevronRight,
    ChevronsLeft,
    ChevronsRight,
    CheckCircle2,
    Loader2,
  } from "lucide-svelte";

  interface Props {
    isRegisterDialogOpen?: boolean;
    onSelectPatientForBooking?: (patient: Patient) => void;
  }

  let {
    isRegisterDialogOpen = $bindable(false),
    onSelectPatientForBooking,
  }: Props = $props();

  // Directory state
  let patients = $state<Patient[]>([]);
  let searchQuery = $state("");
  let isLoading = $state(false);
  let errorMessage = $state<string | null>(null);
  let bannerNotice = $state<string | null>(null);

  // Pagination state
  let pageSize = $state(10);
  let currentPage = $state(1);

  // Registration Dialog State
  let fullName = $state("");
  let contact = $state("");
  let age = $state<string | number>("");
  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});


  // Edit / Delete Dialog State
  let isEditDialogOpen = $state(false);
  let patientForEdit = $state<Patient | null>(null);

  let isDeleteDialogOpen = $state(false);
  let patientForDelete = $state<Patient | null>(null);

  async function loadPatients() {
    isLoading = true;
    errorMessage = null;
    try {
      patients = await api.listPatients();
    } catch (err) {
      const e = err as ApiError;
      errorMessage = e.message || "Failed to load patient records.";
    } finally {
      isLoading = false;
    }
  }

  // Real Hospital Metrics
  let totalPatients = $derived(patients.length);
  let activeAppointmentsCount = $derived(
    patients.filter((p) => (p.appointment_count ?? 0) > 0).length
  );
  let totalConsultationsScheduled = $derived(
    patients.reduce((sum, p) => sum + (p.appointment_count ?? 0), 0)
  );

  // Filtered Patients
  let filteredPatients = $derived.by(() => {
    if (!searchQuery.trim()) return patients;
    const q = searchQuery.toLowerCase().trim();
    return patients.filter(
      (p) =>
        p.full_name.toLowerCase().includes(q) ||
        String(p.id).includes(q) ||
        (p.contact && p.contact.toLowerCase().includes(q))
    );
  });

  // Pagination Derivations & Clamping
  let totalPages = $derived(
    Math.max(1, Math.ceil(filteredPatients.length / pageSize))
  );

  $effect(() => {
    if (currentPage > totalPages) {
      currentPage = totalPages;
    }
  });

  let paginatedPatients = $derived.by(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredPatients.slice(start, start + pageSize);
  });

  let startRecord = $derived(
    filteredPatients.length === 0 ? 0 : (currentPage - 1) * pageSize + 1
  );
  let endRecord = $derived(
    Math.min(currentPage * pageSize, filteredPatients.length)
  );

  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement;
    searchQuery = target.value;
    currentPage = 1;
  }

  function openRegisterDialog() {
    fullName = "";
    contact = "";
    age = "";
    formErrors = {};
    isRegisterDialogOpen = true;
  }

  async function handleRegister(e: SubmitEvent) {
    e.preventDefault();
    formErrors = {};

    const trimmedName = fullName.trim();
    const parsedAge = parseInt(String(age), 10);

    const localErrors: Record<string, string[]> = {};
    if (!trimmedName) localErrors.full_name = ["Full name is required."];
    if (isNaN(parsedAge) || parsedAge <= 0) {
      localErrors.age = ["Age must be a positive whole number greater than 0."];
    }

    if (Object.keys(localErrors).length > 0) {
      formErrors = localErrors;
      return;
    }

    isSubmitting = true;
    try {
      const newPatient = await api.registerPatient({
        full_name: trimmedName,
        contact: contact.trim(),
        age: parsedAge,
      });

      isRegisterDialogOpen = false;
      bannerNotice = `Patient ${newPatient.full_name} registered successfully with ID #${newPatient.id}.`;
      await loadPatients();
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }

  function openQuickBooking(patient: Patient) {
    onSelectPatientForBooking?.(patient);
  }

  function openEditPatient(patient: Patient) {
    patientForEdit = patient;
    isEditDialogOpen = true;
  }

  function openDeletePatient(patient: Patient) {
    patientForDelete = patient;
    isDeleteDialogOpen = true;
  }

  onMount(() => {
    loadPatients();
  });
</script>

<div class="flex flex-col gap-6">
  <!-- Status Banner Notice -->
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
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <div class="flex items-center justify-between">
        <p class="text-sm font-medium text-muted-foreground">Total Enrolled Patients</p>
        <Users class="size-4 text-muted-foreground" />
      </div>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{totalPatients}</p>
      <p class="text-xs text-muted-foreground mt-1">Active primary directory records</p>
    </div>

    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <div class="flex items-center justify-between">
        <p class="text-sm font-medium text-muted-foreground">Patients with Active Schedules</p>
        <CalendarCheck class="size-4 text-primary" />
      </div>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{activeAppointmentsCount}</p>
      <p class="text-xs text-muted-foreground mt-1">Patients with scheduled visits</p>
    </div>

    <div class="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
      <div class="flex items-center justify-between">
        <p class="text-sm font-medium text-muted-foreground">Total Consultations</p>
        <ClipboardList class="size-4 text-muted-foreground" />
      </div>
      <p class="text-2xl font-bold tracking-tight text-foreground mt-2">{totalConsultationsScheduled}</p>
      <p class="text-xs text-muted-foreground mt-1">Lifetime appointment bookings</p>
    </div>
  </div>

  <!-- Table Toolbar Bar (Matching Reference Screenshot) -->
  <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
    <div class="flex items-center gap-2">
      <div class="relative w-full sm:w-72">
        <Search class="absolute left-3 top-2.5 size-4 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          placeholder="Filter patients by name, ID, or phone..."
          value={searchQuery}
          oninput={handleSearchInput}
          class="pl-9 h-9"
        />
      </div>
    </div>

    <div class="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        class="h-9 px-3 cursor-pointer"
        onclick={loadPatients}
        disabled={isLoading}
      >
        {#if isLoading}
          <Loader2 class="size-3.5 animate-spin" />
        {:else}
          <RefreshCw class="size-3.5" />
        {/if}
        <span class="sr-only">Refresh</span>
      </Button>
      <Button onclick={openRegisterDialog} size="sm" class="h-9 px-3 cursor-pointer">
        <UserPlus class="size-3.5 mr-1.5" />
        <span>Register Patient</span>
      </Button>
    </div>
  </div>

  <!-- Table Container (Matching Reference Screenshot) -->
  {#if errorMessage}
    <div class="rounded-xl bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive">
      {errorMessage}
    </div>
  {:else}
    <div class="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-24">Patient ID</TableHead>
            <TableHead>Full Name</TableHead>
            <TableHead>Contact Number</TableHead>
            <TableHead class="w-24 text-center">Age</TableHead>
            <TableHead class="w-32 text-center">Consultations</TableHead>
            <TableHead class="w-16 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {#if isLoading && patients.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-32 text-center text-sm text-muted-foreground">
                <div class="flex items-center justify-center gap-2">
                  <RefreshCw class="animate-spin size-4 text-primary" />
                  <span>Loading patient directory...</span>
                </div>
              </TableCell>
            </TableRow>
          {:else if filteredPatients.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-32 text-center text-sm text-muted-foreground">
                {searchQuery ? "No patients matching your filter query." : "No patients enrolled yet. Click 'Register Patient' to create the first record."}
              </TableCell>
            </TableRow>
          {:else}
            {#each paginatedPatients as patient (patient.id)}
              <TableRow>
                <!-- Patient ID -->
                <TableCell>
                  <Badge variant="outline" class="font-mono text-xs font-normal">
                    #{patient.id}
                  </Badge>
                </TableCell>

                <!-- Full Name -->
                <TableCell class="font-medium text-foreground">
                  {patient.full_name}
                </TableCell>

                <!-- Contact -->
                <TableCell class="text-muted-foreground text-xs font-mono">
                  {patient.contact || "None provided"}
                </TableCell>

                <!-- Age -->
                <TableCell class="text-center tabular-nums text-foreground">
                  {patient.age}
                </TableCell>

                <!-- Consultation count -->
                <TableCell class="text-center">
                  <Badge variant="secondary" class="text-xs font-mono">
                    {patient.appointment_count ?? 0}
                  </Badge>
                </TableCell>

                <!-- Three-Dots Dropdown Menu -->
                <TableCell class="text-right">
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger class="inline-flex items-center justify-center rounded-md size-8 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-ring">
                      <MoreHorizontal class="size-4" />
                      <span class="sr-only">Open menu</span>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Content align="end">
                      <DropdownMenu.Item onclick={() => openQuickBooking(patient)} class="cursor-pointer">
                        <CalendarPlus class="size-4 mr-2" />
                        <span>Book Appointment</span>
                      </DropdownMenu.Item>
                      <DropdownMenu.Item onclick={() => openEditPatient(patient)} class="cursor-pointer">
                        <Pencil class="size-4 mr-2" />
                        <span>Edit Details</span>
                      </DropdownMenu.Item>
                      <DropdownMenu.Separator />
                      <DropdownMenu.Item
                        onclick={() => openDeletePatient(patient)}
                        class="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
                      >
                        <Trash2 class="size-4 mr-2" />
                        <span>Delete Patient</span>
                      </DropdownMenu.Item>
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
            Showing {startRecord} to {endRecord} of {filteredPatients.length} record(s)
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

  <!-- Modal Dialog: Register Patient -->
  <Dialog.Root bind:open={isRegisterDialogOpen}>
    <Dialog.Content class="sm:max-w-md">
      <Dialog.Header>
        <Dialog.Title>Register New Patient</Dialog.Title>
        <Dialog.Description>
          Enter patient clinical records. A unique numerical ID will be assigned automatically.
        </Dialog.Description>
      </Dialog.Header>

      <form onsubmit={handleRegister} class="flex flex-col gap-4 py-2">
        <!-- Full Name -->
        <div>
          <label for="regFullName" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Full Name <span class="text-destructive">*</span>
          </label>
          <Input
            id="regFullName"
            type="text"
            placeholder="e.g. Maria Santos"
            bind:value={fullName}
            aria-invalid={!!formErrors.full_name}
            disabled={isSubmitting}
            autofocus
          />
          {#if formErrors.full_name}
            <p class="text-xs text-destructive mt-1">{formErrors.full_name.join(" ")}</p>
          {/if}
        </div>

        <!-- Contact Number -->
        <div>
          <label for="regContact" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Contact Number <span class="font-normal text-muted-foreground/70 lowercase">(optional)</span>
          </label>
          <Input
            id="regContact"
            type="text"
            placeholder="e.g. 0917-123-4567"
            bind:value={contact}
            aria-invalid={!!formErrors.contact}
            disabled={isSubmitting}
          />
          {#if formErrors.contact}
            <p class="text-xs text-destructive mt-1">{formErrors.contact.join(" ")}</p>
          {/if}
        </div>

        <!-- Age -->
        <div>
          <label for="regAge" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Age <span class="text-destructive">*</span>
          </label>
          <Input
            id="regAge"
            type="number"
            min="1"
            placeholder="e.g. 28"
            bind:value={age}
            aria-invalid={!!formErrors.age}
            disabled={isSubmitting}
          />
          {#if formErrors.age}
            <p class="text-xs text-destructive mt-1">{formErrors.age.join(" ")}</p>
          {/if}
        </div>

        {#if formErrors.general}
          <div class="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
            {formErrors.general.join(" ")}
          </div>
        {/if}

        <Dialog.Footer class="pt-2">
          <Button
            type="button"
            variant="outline"
            onclick={() => (isRegisterDialogOpen = false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="size-4 animate-spin" />
            {/if}
            Register Patient
          </Button>
        </Dialog.Footer>
      </form>
    </Dialog.Content>
  </Dialog.Root>

  <!-- Edit Patient Dialog -->
  <EditPatientDialog
    bind:open={isEditDialogOpen}
    patient={patientForEdit}
    onSuccess={() => {
      bannerNotice = `Patient details for ${patientForEdit?.full_name} updated successfully.`;
      loadPatients();
    }}
  />

  <!-- Delete Patient Dialog -->
  <DeletePatientDialog
    bind:open={isDeleteDialogOpen}
    patient={patientForDelete}
    onSuccess={() => {
      bannerNotice = `Patient record #${patientForDelete?.id} deleted successfully.`;
      loadPatients();
    }}
  />
</div>
