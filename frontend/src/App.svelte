<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient } from "$lib/api";
  import PatientsWorkspace from "./components/PatientsWorkspace.svelte";
  import AppointmentsWorkspace from "./components/AppointmentsWorkspace.svelte";

  type Workspace = "patients" | "appointments";
  let activeWorkspace = $state<Workspace>("patients");
  let selectedPatientForBooking = $state<Patient | null>(null);

  let isOnline = $state(false);
  let globalError = $state<string | null>(null);

  function handleSelectPatientForBooking(patient: Patient) {
    selectedPatientForBooking = patient;
    activeWorkspace = "appointments";
  }

  async function checkHealth() {
    try {
      const res = await api.healthCheck();
      if (res.status === "ok") {
        isOnline = true;
      }
    } catch {
      isOnline = false;
    }
  }

  onMount(() => {
    checkHealth();

    // Global Error Boundary listener
    window.addEventListener("error", (event) => {
      globalError = event.message || "An unexpected interface error occurred.";
    });

    window.addEventListener("unhandledrejection", (event) => {
      globalError = event.reason?.message || "An unhandled promise rejection occurred.";
    });
  });
</script>

<div class="min-h-screen bg-[#FAF9F6] text-stone-900 flex flex-col selection:bg-teal-100 selection:text-teal-900">
  <!-- Top Navigation Header -->
  <header class="border-b border-stone-200 bg-white/95 backdrop-blur sticky top-0 z-40 shadow-xs">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <!-- Clinic Emblem & Title -->
      <div class="flex items-center space-x-3">
        <div class="h-9 w-9 rounded-lg bg-[#0F766E] flex items-center justify-center text-white shadow-xs">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
          </svg>
        </div>
        <div>
          <h1 class="text-base font-bold tracking-tight text-stone-900 leading-tight">
            Hospital Management System
          </h1>
          <p class="text-[11px] text-stone-500 font-medium leading-none">
            Local Desktop Coursework Edition
          </p>
        </div>
      </div>

      <!-- Center Workspaces Switcher -->
      <nav class="flex items-center p-1 bg-stone-100/80 rounded-lg border border-stone-200">
        <button
          class="px-4 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer {activeWorkspace === 'patients' ? 'bg-white text-[#0F766E] shadow-xs' : 'text-stone-600 hover:text-stone-900'}"
          onclick={() => (activeWorkspace = "patients")}
        >
          Patients
        </button>
        <button
          class="px-4 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer {activeWorkspace === 'appointments' ? 'bg-white text-[#0F766E] shadow-xs' : 'text-stone-600 hover:text-stone-900'}"
          onclick={() => (activeWorkspace = "appointments")}
        >
          Appointments
        </button>
      </nav>

      <!-- Connection Status Pill -->
      <div class="flex items-center space-x-2 text-xs">
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium {isOnline ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-stone-100 text-stone-500'}">
          <span class="h-1.5 w-1.5 rounded-full {isOnline ? 'bg-emerald-500' : 'bg-stone-400'}"></span>
          <span>{isOnline ? "Local Core Connected" : "Connecting..."}</span>
        </span>
      </div>
    </div>
  </header>

  <!-- Global Error Banner if caught -->
  {#if globalError}
    <div class="bg-rose-50 border-b border-rose-200 text-rose-800 px-4 py-3 text-xs flex items-center justify-between">
      <span><strong>Interface Alert:</strong> {globalError}</span>
      <button onclick={() => (globalError = null)} class="text-rose-700 font-bold underline ml-4 cursor-pointer">
        Dismiss
      </button>
    </div>
  {/if}

  <!-- Main Workspaces Canvas -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
    {#if activeWorkspace === "patients"}
      <PatientsWorkspace onSelectPatientForBooking={handleSelectPatientForBooking} />
    {:else if activeWorkspace === "appointments"}
      <AppointmentsWorkspace preselectedPatient={selectedPatientForBooking} />
    {/if}
  </main>

  <!-- Footer -->
  <footer class="border-t border-stone-200 bg-white py-4 text-center text-xs text-stone-400">
    <p>HospitalSystem &bull; Offline Desktop Workspace &bull; Svelte + Django + pywebview</p>
  </footer>
</div>
