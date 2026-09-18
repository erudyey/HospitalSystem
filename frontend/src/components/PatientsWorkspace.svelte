<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient, type ApiError } from "$lib/api";
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
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    Copy,
    Check,
    X,
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

  // Sorting state
  type PatientSortField = "id" | "full_name" | "contact" | "age" | "appointment_count";
  let sortField = $state<PatientSortField>("id");
  let sortDirection = $state<"asc" | "desc">("desc");

  // Clipboard feedback state
  let copiedText = $state<string | null>(null);

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

  // Hospital Metrics
  let totalPatients = $derived(patients.length);
  let activeAppointmentsCount = $derived(
    patients.filter((p) => (p.active_appointment_count ?? 0) > 0).length
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

  // Sorting Derivation
  let sortedPatients = $derived.by(() => {
    const list = [...filteredPatients];
    return list.sort((a, b) => {
      let cmp = 0;
      if (sortField === "id") {
        cmp = a.id - b.id;
      } else if (sortField === "full_name") {
        cmp = a.full_name.localeCompare(b.full_name);
      } else if (sortField === "contact") {
        cmp = (a.contact || "").localeCompare(b.contact || "");
      } else if (sortField === "age") {
        cmp = a.age - b.age;
      } else if (sortField === "appointment_count") {
        cmp = (a.appointment_count ?? 0) - (b.appointment_count ?? 0);
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });
  });

  function toggleSort(field: PatientSortField) {
    if (sortField === field) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDirection = field === "full_name" ? "asc" : "desc";
    }
    currentPage = 1;
  }

  // Pagination Derivations & Clamping
  let totalPages = $derived(
    Math.max(1, Math.ceil(sortedPatients.length / pageSize))
  );

  $effect(() => {
    if (currentPage > totalPages) {
      currentPage = totalPages;
    }
  });

  let paginatedPatients = $derived.by(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedPatients.slice(start, start + pageSize);
  });

  let startRecord = $derived(
    sortedPatients.length === 0 ? 0 : (currentPage - 1) * pageSize + 1
  );
  let endRecord = $derived(
    Math.min(currentPage * pageSize, sortedPatients.length)
  );

  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement;
    searchQuery = target.value;
    currentPage = 1;
  }

  function clearSearch() {
    searchQuery = "";
    currentPage = 1;
  }

  async function copyToClipboard(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      copiedText = text;
      toast.info(`Copied ${label} to clipboard.`);
      setTimeout(() => {
        if (copiedText === text) copiedText = null;
      }, 1500);
    } catch {
      toast.error("Failed to copy to clipboard.");
    }
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
      toast.success(`Patient ${newPatient.full_name} registered with ID #${newPatient.id}.`);
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
    </div>

    <div class="flex items-center gap-2">
      {#if totalPages > 1}
        <div class="hidden sm:flex items-center gap-1.5 mr-1 text-xs text-muted-foreground border-r border-border pr-2.5">
          <span class="font-medium text-foreground tabular-nums">
            {currentPage}/{totalPages}
          </span>
          <button
            type="button"
            class="p-1 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            onclick={() => (currentPage = Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            title="Previous Page"
          >
            <ChevronLeft class="size-3.5" />
          </button>
          <button
            type="button"
            class="p-1 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            title="Next Page"
          >
            <ChevronRight class="size-3.5" />
          </button>
        </div>
      {/if}

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
    <div class="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col">
      <Table containerClass="max-h-[calc(100vh-340px)] min-h-[240px]">
        <TableHeader class="sticky top-0 bg-card z-10 shadow-xs border-b [&_tr]:bg-card">
          <TableRow>
            <TableHead class="w-28">
              <button
                type="button"
                onclick={() => toggleSort("id")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Patient ID
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
                onclick={() => toggleSort("full_name")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Full Name
                {#if sortField === "full_name"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead>
              <button
                type="button"
                onclick={() => toggleSort("contact")}
                class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs"
              >
                Contact Number
                {#if sortField === "contact"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead class="w-24 text-center">
              <button
                type="button"
                onclick={() => toggleSort("age")}
                class="inline-flex items-center justify-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs w-full"
              >
                Age
                {#if sortField === "age"}
                  {#if sortDirection === "asc"}<ArrowUp class="size-3 text-primary" />{:else}<ArrowDown class="size-3 text-primary" />{/if}
                {:else}
                  <ArrowUpDown class="size-3 opacity-40" />
                {/if}
              </button>
            </TableHead>
            <TableHead class="w-32 text-center">
              <button
                type="button"
                onclick={() => toggleSort("appointment_count")}
                class="inline-flex items-center justify-center gap-1.5 hover:text-foreground transition-colors cursor-pointer font-semibold text-xs w-full"
              >
                Consultations
                {#if sortField === "appointment_count"}
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
          {#if isLoading && patients.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-32 text-center text-sm text-muted-foreground">
                <div class="flex items-center justify-center gap-2">
                  <RefreshCw class="animate-spin size-4 text-primary" />
                  <span>Loading patient directory...</span>
                </div>
              </TableCell>
            </TableRow>
          {:else if sortedPatients.length === 0}
            <TableRow>
              <TableCell colspan={6} class="h-36 text-center text-sm text-muted-foreground">
                {#if searchQuery}
                  <div class="flex flex-col items-center justify-center gap-2 py-2">
                    <p>No patients matching the filter "{searchQuery}".</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onclick={clearSearch}
                      class="cursor-pointer"
                    >
                      Clear Search Filter
                    </Button>
                  </div>
                {:else}
                  No patients enrolled yet. Click 'Register Patient' to create the first record.
                {/if}
              </TableCell>
            </TableRow>
          {:else}
            {#each paginatedPatients as patient (patient.id)}
              <TableRow>
                <!-- Patient ID with copy -->
                <TableCell>
                  <button
                    type="button"
                    onclick={() => copyToClipboard(String(patient.id), `ID #${patient.id}`)}
                    class="group inline-flex items-center gap-1.5 cursor-pointer text-left"
                    title="Click to copy patient ID"
                  >
                    <Badge variant="outline" class="font-mono text-xs font-normal group-hover:border-primary/50 transition-colors">
                      #{patient.id}
                    </Badge>
                    {#if copiedText === String(patient.id)}
                      <Check class="size-3 text-emerald-600 shrink-0" />
                    {:else}
                      <Copy class="size-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                    {/if}
                  </button>
                </TableCell>

                <!-- Full Name -->
                <TableCell class="font-medium text-foreground">
                  {patient.full_name}
                </TableCell>

                <!-- Contact with copy -->
                <TableCell class="text-muted-foreground text-xs font-mono">
                  {#if patient.contact}
                    <button
                      type="button"
                      onclick={() => copyToClipboard(patient.contact, "contact number")}
                      class="group inline-flex items-center gap-1.5 hover:text-foreground cursor-pointer transition-colors"
                      title="Click to copy contact"
                    >
                      <span>{patient.contact}</span>
                      {#if copiedText === patient.contact}
                        <Check class="size-3 text-emerald-600 shrink-0" />
                      {:else}
                        <Copy class="size-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      {/if}
                    </button>
                  {:else}
                    <span class="text-muted-foreground/60 italic">None provided</span>
                  {/if}
                </TableCell>

                <!-- Age -->
                <TableCell class="text-center tabular-nums text-foreground">
                  {patient.age}
                </TableCell>

                <!-- Consultation count -->
                <TableCell class="text-center">
                  <div class="inline-flex items-center justify-center gap-1.5 w-full">
                    <Badge variant="secondary" class="text-xs font-mono">
                      {patient.appointment_count ?? 0}
                    </Badge>
                    {#if (patient.active_appointment_count ?? 0) > 0}
                      <span class="size-1.5 rounded-full bg-sky-500 shrink-0" title="{patient.active_appointment_count} active scheduled visit(s)"></span>
                    {/if}
                  </div>
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
      toast.success(`Patient details for ${patientForEdit?.full_name} updated.`);
      loadPatients();
    }}
  />

  <!-- Delete Patient Dialog -->
  <DeletePatientDialog
    bind:open={isDeleteDialogOpen}
    patient={patientForDelete}
    onSuccess={() => {
      toast.success(`Patient record #${patientForDelete?.id} deleted.`);
      loadPatients();
    }}
  />
</div>
