<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient, type ApiError } from "$lib/api";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import Card from "$lib/components/ui/Card.svelte";
  import CardHeader from "$lib/components/ui/CardHeader.svelte";
  import CardTitle from "$lib/components/ui/CardTitle.svelte";
  import CardContent from "$lib/components/ui/CardContent.svelte";
  import Table from "$lib/components/ui/Table.svelte";
  import TableHeader from "$lib/components/ui/TableHeader.svelte";
  import TableHead from "$lib/components/ui/TableHead.svelte";
  import TableBody from "$lib/components/ui/TableBody.svelte";
  import TableRow from "$lib/components/ui/TableRow.svelte";
  import TableCell from "$lib/components/ui/TableCell.svelte";

  interface Props {
    onSelectPatientForBooking?: (patient: Patient) => void;
  }

  let { onSelectPatientForBooking }: Props = $props();

  // Registration form state
  let fullName = $state("");
  let contact = $state("");
  let age = $state<string | number>("");
  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});
  let successMessage = $state<string | null>(null);

  // Directory / Search state
  let searchQuery = $state("");
  let patients = $state<Patient[]>([]);
  let isLoadingDirectory = $state(false);
  let directoryError = $state<string | null>(null);

  async function loadPatients(query = "") {
    isLoadingDirectory = true;
    directoryError = null;
    try {
      patients = await api.listPatients(query);
    } catch (err) {
      const e = err as ApiError;
      directoryError = e.message || "Failed to load patient directory.";
    } finally {
      isLoadingDirectory = false;
    }
  }

  async function handleRegister(e: SubmitEvent) {
    e.preventDefault();
    formErrors = {};
    successMessage = null;

    const trimmedName = fullName.trim();
    const parsedAge = parseInt(String(age), 10);

    // Client-side quick guard
    const localErrors: Record<string, string[]> = {};
    if (!trimmedName) localErrors.full_name = ["Full name is required."];
    if (isNaN(parsedAge) || parsedAge <= 0) localErrors.age = ["Age must be a positive whole number greater than 0."];

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

      successMessage = `Patient registered successfully! Assigned ID: #${newPatient.id}`;
      fullName = "";
      contact = "";
      age = "";
      
      // Refresh directory list
      await loadPatients(searchQuery);
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }

  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement;
    searchQuery = target.value;
    loadPatients(searchQuery);
  }

  function handleClearForm() {
    fullName = "";
    contact = "";
    age = "";
    formErrors = {};
    successMessage = null;
  }

  onMount(() => {
    loadPatients();
  });
</script>

<div class="space-y-8">
  <!-- Top: Notice Banner if any -->
  {#if successMessage}
    <div class="rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800 flex items-center justify-between shadow-sm">
      <div class="flex items-center space-x-2">
        <svg class="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span class="font-medium">{successMessage}</span>
      </div>
      <button onclick={() => (successMessage = null)} class="text-emerald-700 hover:text-emerald-900 text-xs font-semibold cursor-pointer">Dismiss</button>
    </div>
  {/if}

  <!-- Golden Ratio Split Layout: 38.2% Form, 61.8% Directory -->
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
    <!-- Registration Card (38.2% on desktop -> col-span-5) -->
    <div class="lg:col-span-5">
      <Card>
        <CardHeader>
          <CardTitle>Register New Patient</CardTitle>
          <p class="text-xs text-stone-500 mt-1">Enroll patient into the local clinic records. Numerical IDs are assigned automatically.</p>
        </CardHeader>
        <CardContent>
          <form onsubmit={handleRegister} class="space-y-4">
            <!-- Full Name -->
            <div>
              <label for="fullName" class="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
                Full Name <span class="text-rose-500">*</span>
              </label>
              <Input
                id="fullName"
                type="text"
                placeholder="e.g. Maria Santos"
                bind:value={fullName}
                error={!!formErrors.full_name}
                disabled={isSubmitting}
              />
              {#if formErrors.full_name}
                <p class="text-xs text-rose-600 mt-1">{formErrors.full_name.join(" ")}</p>
              {/if}
            </div>

            <!-- Contact -->
            <div>
              <label for="contact" class="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
                Contact Number <span class="text-stone-400 font-normal lowercase">(optional)</span>
              </label>
              <Input
                id="contact"
                type="text"
                placeholder="e.g. 0917-123-4567"
                bind:value={contact}
                error={!!formErrors.contact}
                disabled={isSubmitting}
              />
              {#if formErrors.contact}
                <p class="text-xs text-rose-600 mt-1">{formErrors.contact.join(" ")}</p>
              {/if}
            </div>

            <!-- Age -->
            <div>
              <label for="age" class="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
                Age <span class="text-rose-500">*</span>
              </label>
              <Input
                id="age"
                type="number"
                min="1"
                placeholder="e.g. 28"
                bind:value={age}
                error={!!formErrors.age}
                disabled={isSubmitting}
              />
              {#if formErrors.age}
                <p class="text-xs text-rose-600 mt-1">{formErrors.age.join(" ")}</p>
              {/if}
            </div>

            {#if formErrors.general}
              <div class="rounded-md bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                {formErrors.general.join(" ")}
              </div>
            {/if}

            <!-- Buttons -->
            <div class="pt-2 flex items-center space-x-3">
              <Button type="submit" loading={isSubmitting} class="w-full">
                Register Patient
              </Button>
              <Button type="button" variant="outline" onclick={handleClearForm} disabled={isSubmitting}>
                Clear
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>

    <!-- Patient Directory (61.8% on desktop -> col-span-7) -->
    <div class="lg:col-span-7">
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-4">
          <div>
            <CardTitle>Patient Directory</CardTitle>
            <p class="text-xs text-stone-500 mt-1">Search records by name or exact patient ID.</p>
          </div>
          <Button variant="outline" size="sm" onclick={() => loadPatients(searchQuery)} loading={isLoadingDirectory}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          <!-- Search Bar -->
          <div class="mb-4">
            <Input
              type="text"
              placeholder="Search by patient name or numeric ID..."
              value={searchQuery}
              oninput={handleSearchInput}
            />
          </div>

          <!-- Directory Table -->
          {#if directoryError}
            <div class="rounded-md bg-rose-50 border border-rose-200 p-4 text-sm text-rose-700">
              {directoryError}
            </div>
          {:else if patients.length === 0}
            <div class="text-center py-12 px-4 border border-dashed border-stone-200 rounded-lg">
              <svg class="mx-auto h-10 w-10 text-stone-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              <h4 class="text-sm font-medium text-stone-700">No patients found</h4>
              <p class="text-xs text-stone-500 mt-1">
                {searchQuery ? "No matching records found for this search." : "Register a patient using the form on the left to start."}
              </p>
            </div>
          {:else}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead class="w-16">ID</TableHead>
                  <TableHead>Full Name</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead class="w-16 text-center">Age</TableHead>
                  <TableHead class="w-24 text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {#each patients as patient (patient.id)}
                  <TableRow>
                    <TableCell class="font-mono text-xs font-semibold text-teal-800">
                      <Badge variant="id">#{patient.id}</Badge>
                    </TableCell>
                    <TableCell class="font-medium text-stone-900">
                      {patient.full_name}
                    </TableCell>
                    <TableCell class="text-stone-600 text-xs">
                      {patient.contact || "—"}
                    </TableCell>
                    <TableCell class="text-center tabular-nums text-stone-700">
                      {patient.age}
                    </TableCell>
                    <TableCell class="text-right">
                      {#if onSelectPatientForBooking}
                        <Button
                          variant="ghost"
                          size="sm"
                          class="text-teal-700 hover:text-teal-800 hover:bg-teal-50 text-xs h-7 px-2"
                          onclick={() => onSelectPatientForBooking(patient)}
                        >
                          Book Appt
                        </Button>
                      {/if}
                    </TableCell>
                  </TableRow>
                {/each}
              </TableBody>
            </Table>
          {/if}
        </CardContent>
      </Card>
    </div>
  </div>
</div>
