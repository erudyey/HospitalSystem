<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient, type Appointment, type ApiError } from "$lib/api";
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
    preselectedPatient?: Patient | null;
  }

  let { preselectedPatient = null }: Props = $props();

  // All patients for dropdown selector
  let patientList = $state<Patient[]>([]);
  let selectedPatientId = $state<number | null>(null);

  // Appointments for currently selected patient
  let appointments = $state<Appointment[]>([]);
  let isLoadingAppointments = $state(false);
  let appointmentError = $state<string | null>(null);

  // Booking Form State
  let doctorName = $state("");
  let appDate = $state(new Date().toISOString().split("T")[0]);
  let isBooking = $state(false);
  let bookingErrors = $state<Record<string, string[]>>({});
  let successNotice = $state<string | null>(null);

  // Status update state
  let updatingAppId = $state<number | null>(null);

  // Abort controller to prevent race conditions when switching patients
  let currentAbortController: AbortController | null = null;

  async function loadPatientList() {
    try {
      patientList = await api.listPatients();
      if (!selectedPatientId && patientList.length > 0) {
        selectedPatientId = patientList[0].id;
        loadAppointmentsForPatient(selectedPatientId);
      }
    } catch {
      // Ignored in list fetch
    }
  }

  async function loadAppointmentsForPatient(patientId: number | null) {
    if (patientId === null) {
      appointments = [];
      return;
    }

    // Cancel in-flight request if user switches patient quickly
    if (currentAbortController) {
      currentAbortController.abort();
    }
    currentAbortController = new AbortController();

    isLoadingAppointments = true;
    appointmentError = null;

    try {
      appointments = await api.listPatientAppointments(patientId, currentAbortController.signal);
    } catch (err) {
      const e = err as { name?: string; message?: string };
      if (e.name === "AbortError") {
        return; // Ignore cancelled requests
      }
      appointmentError = e.message || "Failed to load appointments.";
    } finally {
      isLoadingAppointments = false;
    }
  }

  function handlePatientChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    const newId = target.value ? parseInt(target.value, 10) : null;
    selectedPatientId = newId;
    successNotice = null;
    bookingErrors = {};
    loadAppointmentsForPatient(newId);
  }

  async function handleBookAppointment(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedPatientId) {
      bookingErrors = { general: ["Please select a patient before booking an appointment."] };
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

    isBooking = true;
    bookingErrors = {};
    successNotice = null;

    try {
      const newApp = await api.bookAppointment({
        patient_id: selectedPatientId,
        doctor_name: trimmedDoctor,
        app_date: appDate,
      });

      doctorName = "";
      successNotice = `Appointment #${newApp.id} booked with ${newApp.doctor_name} for ${newApp.app_date}.`;
      await loadAppointmentsForPatient(selectedPatientId);
    } catch (err) {
      const e = err as ApiError;
      bookingErrors = e.fields || { general: [e.message] };
    } finally {
      isBooking = false;
    }
  }

  async function handleStatusChange(appointmentId: number, status: "Completed" | "Cancelled") {
    updatingAppId = appointmentId;
    successNotice = null;

    try {
      const updated = await api.updateAppointmentStatus(appointmentId, status);
      successNotice = `Appointment #${updated.id} marked as ${updated.status}.`;
      if (selectedPatientId) {
        await loadAppointmentsForPatient(selectedPatientId);
      }
    } catch (err) {
      const e = err as ApiError;
      alert(`Status update failed: ${e.message}`);
    } finally {
      updatingAppId = null;
    }
  }

  $effect(() => {
    if (preselectedPatient && preselectedPatient.id !== selectedPatientId) {
      selectedPatientId = preselectedPatient.id;
      loadAppointmentsForPatient(selectedPatientId);
    }
  });

  onMount(() => {
    loadPatientList();
  });
</script>

<div class="space-y-8">
  <!-- Top Notice -->
  {#if successNotice}
    <div class="rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800 flex items-center justify-between shadow-sm">
      <div class="flex items-center space-x-2">
        <svg class="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span class="font-medium">{successNotice}</span>
      </div>
      <button onclick={() => (successNotice = null)} class="text-emerald-700 hover:text-emerald-900 text-xs font-semibold cursor-pointer">Dismiss</button>
    </div>
  {/if}

  <!-- Patient Selector Bar -->
  <Card class="bg-gradient-to-r from-stone-50 to-white border-stone-200">
    <CardContent class="py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div class="flex items-center space-x-3 w-full md:w-auto">
        <label for="patientSelector" class="text-xs font-bold uppercase tracking-wider text-stone-600 whitespace-nowrap">
          Active Patient:
        </label>
        <select
          id="patientSelector"
          class="h-10 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 focus:outline-none focus:ring-2 focus:ring-[#0F766E] w-full md:w-80 shadow-sm cursor-pointer"
          value={selectedPatientId || ""}
          onchange={handlePatientChange}
        >
          <option value="" disabled>-- Choose a patient --</option>
          {#each patientList as p (p.id)}
            <option value={p.id}>
              {p.full_name} (ID: #{p.id}) - Age {p.age}
            </option>
          {/each}
        </select>
      </div>

      <div class="flex items-center space-x-2">
        <Button variant="outline" size="sm" onclick={loadPatientList}>
          Refresh Patients
        </Button>
      </div>
    </CardContent>
  </Card>

  <!-- Golden Ratio Split: 38.2% Form, 61.8% History Table -->
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
    <!-- Booking Form (38.2% -> col-span-5) -->
    <div class="lg:col-span-5">
      <Card>
        <CardHeader>
          <CardTitle>Book Appointment</CardTitle>
          <p class="text-xs text-stone-500 mt-1">Schedule a consultation for the active patient.</p>
        </CardHeader>
        <CardContent>
          {#if !selectedPatientId}
            <div class="text-center py-8 text-stone-500 text-sm">
              Please select a patient from the dropdown above to book an appointment.
            </div>
          {:else}
            <form onsubmit={handleBookAppointment} class="space-y-4">
              <!-- Doctor Name -->
              <div>
                <label for="doctorName" class="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
                  Doctor Name <span class="text-rose-500">*</span>
                </label>
                <Input
                  id="doctorName"
                  type="text"
                  placeholder="e.g. Dr. Maria Cruz"
                  bind:value={doctorName}
                  error={!!bookingErrors.doctor_name}
                  disabled={isBooking}
                />
                {#if bookingErrors.doctor_name}
                  <p class="text-xs text-rose-600 mt-1">{bookingErrors.doctor_name.join(" ")}</p>
                {/if}
              </div>

              <!-- Date Picker -->
              <div>
                <label for="appDate" class="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
                  Appointment Date (YYYY-MM-DD) <span class="text-rose-500">*</span>
                </label>
                <Input
                  id="appDate"
                  type="date"
                  bind:value={appDate}
                  error={!!bookingErrors.app_date}
                  disabled={isBooking}
                />
                {#if bookingErrors.app_date}
                  <p class="text-xs text-rose-600 mt-1">{bookingErrors.app_date.join(" ")}</p>
                {/if}
              </div>

              {#if bookingErrors.general}
                <div class="rounded-md bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                  {bookingErrors.general.join(" ")}
                </div>
              {/if}

              <Button type="submit" loading={isBooking} class="w-full mt-2">
                Confirm Booking
              </Button>
            </form>
          {/if}
        </CardContent>
      </Card>
    </div>

    <!-- Appointment History Table (61.8% -> col-span-7) -->
    <div class="lg:col-span-7">
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-4">
          <div>
            <CardTitle>Appointment History</CardTitle>
            <p class="text-xs text-stone-500 mt-1">Consultation schedule and status updates.</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={!selectedPatientId || isLoadingAppointments}
            onclick={() => loadAppointmentsForPatient(selectedPatientId)}
          >
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {#if !selectedPatientId}
            <div class="text-center py-12 text-stone-400 text-sm">
              Select a patient above to view appointment records.
            </div>
          {:else if isLoadingAppointments}
            <div class="py-12 text-center text-sm text-stone-500 flex items-center justify-center space-x-2">
              <svg class="animate-spin h-5 w-5 text-teal-700" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Loading patient appointments...</span>
            </div>
          {:else if appointmentError}
            <div class="rounded-md bg-rose-50 border border-rose-200 p-4 text-sm text-rose-700">
              {appointmentError}
            </div>
          {:else if appointments.length === 0}
            <div class="text-center py-12 px-4 border border-dashed border-stone-200 rounded-lg">
              <svg class="mx-auto h-10 w-10 text-stone-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <h4 class="text-sm font-medium text-stone-700">No appointments scheduled</h4>
              <p class="text-xs text-stone-500 mt-1">Book an appointment using the form on the left.</p>
            </div>
          {:else}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead class="w-14">Appt #</TableHead>
                  <TableHead>Doctor</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead class="w-28 text-center">Status</TableHead>
                  <TableHead class="w-36 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {#each appointments as app (app.id)}
                  <TableRow>
                    <TableCell class="font-mono text-xs font-semibold text-stone-600">
                      #{app.id}
                    </TableCell>
                    <TableCell class="font-medium text-stone-900">
                      {app.doctor_name}
                    </TableCell>
                    <TableCell class="tabular-nums text-xs text-stone-600">
                      {app.app_date}
                    </TableCell>
                    <TableCell class="text-center">
                      {#if app.status === "Scheduled"}
                        <Badge variant="scheduled">Scheduled</Badge>
                      {:else if app.status === "Completed"}
                        <Badge variant="completed">Completed</Badge>
                      {:else if app.status === "Cancelled"}
                        <Badge variant="cancelled">Cancelled</Badge>
                      {/if}
                    </TableCell>
                    <TableCell class="text-right space-x-1">
                      {#if app.status === "Scheduled"}
                        <Button
                          variant="outline"
                          size="sm"
                          class="h-7 text-xs px-2 text-emerald-700 border-emerald-200 hover:bg-emerald-50"
                          loading={updatingAppId === app.id}
                          onclick={() => handleStatusChange(app.id, "Completed")}
                        >
                          Complete
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-7 text-xs px-2 text-rose-700 hover:bg-rose-50"
                          loading={updatingAppId === app.id}
                          onclick={() => handleStatusChange(app.id, "Cancelled")}
                        >
                          Cancel
                        </Button>
                      {:else if app.status === "Completed"}
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-7 text-xs px-2 text-rose-700 hover:bg-rose-50"
                          loading={updatingAppId === app.id}
                          onclick={() => handleStatusChange(app.id, "Cancelled")}
                        >
                          Cancel
                        </Button>
                      {:else if app.status === "Cancelled"}
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-7 text-xs px-2 text-emerald-700 hover:bg-emerald-50"
                          loading={updatingAppId === app.id}
                          onclick={() => handleStatusChange(app.id, "Completed")}
                        >
                          Restore
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
