<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Patient } from "$lib/api";
  import { cn } from "$lib/utils";
  import PatientsWorkspace from "./components/PatientsWorkspace.svelte";
  import AppointmentsWorkspace from "./components/AppointmentsWorkspace.svelte";
  import ToastContainer from "$lib/components/ToastContainer.svelte";
  import {
    Users,
    Calendar,
    SquarePlus,
    UserPlus,
  } from "lucide-svelte";

  type Workspace = "patients" | "appointments";
  let activeWorkspace = $state<Workspace>("patients");
  let selectedPatientForBooking = $state<Patient | null>(null);

  let isOnline = $state(false);
  let globalError = $state<string | null>(null);

  // Trigger modal flags for quick actions in the sidebar
  let triggerPatientRegister = $state(false);
  let triggerAppointmentBook = $state(false);

  function handleSelectPatientForBooking(patient: Patient) {
    selectedPatientForBooking = patient;
    activeWorkspace = "appointments";
  }

  function handleClearSelectedPatient() {
    selectedPatientForBooking = null;
  }

  function handleQuickRegisterPatient() {
    activeWorkspace = "patients";
    triggerPatientRegister = true;
  }

  function handleQuickBookAppointment() {
    activeWorkspace = "appointments";
    triggerAppointmentBook = true;
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

    // Global keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      // Alt+1: Patients, Alt+2: Appointments
      if (e.altKey && e.key === "1") {
        e.preventDefault();
        activeWorkspace = "patients";
      } else if (e.altKey && e.key === "2") {
        e.preventDefault();
        activeWorkspace = "appointments";
      } else if (
        ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") ||
        (e.key === "/" && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement))
      ) {
        e.preventDefault();
        const searchEl = document.querySelector<HTMLInputElement>('input[data-search-input="true"]');
        if (searchEl) {
          searchEl.focus();
          searchEl.select();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  });
</script>

<div class="h-screen bg-background text-foreground flex flex-row selection:bg-primary/10 selection:text-primary antialiased overflow-hidden">
  <!-- Left Sidebar Navigation -->
  <aside class="w-64 border-r border-border bg-card flex flex-col shrink-0 h-screen select-none">
    <!-- Clinic Brand Header (Cross in a Box Icon) -->
    <div class="px-4 h-14 border-b border-border flex items-center gap-2.5">
      <div class="size-7 rounded-lg bg-primary text-primary-foreground flex items-center justify-center shrink-0 shadow-xs">
        <SquarePlus class="size-4" />
      </div>
      <div>
        <h1 class="text-sm font-semibold tracking-tight text-foreground leading-tight">
          Hospital System
        </h1>
      </div>
    </div>

    <!-- Quick Action CTA Button (Sidebar) -->
    <div class="p-3 border-b border-border">
      <button
        onclick={handleQuickRegisterPatient}
        class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-xs font-medium h-8 px-3 bg-primary text-primary-foreground shadow hover:bg-primary/90 transition-colors cursor-pointer"
      >
        <UserPlus class="size-3.5" />
        <span>+ Register Patient</span>
      </button>
    </div>

    <!-- Navigation Workspace Switcher -->
    <div class="flex-1 py-3 px-2 flex flex-col gap-1 overflow-y-auto">
      <p class="text-[11px] font-medium text-muted-foreground px-2.5 py-1">
        Clinical Records
      </p>
      <button
        onclick={() => (activeWorkspace = "patients")}
        class={cn(
          "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer",
          activeWorkspace === "patients"
            ? "bg-muted text-foreground font-semibold shadow-xs"
            : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        )}
      >
        <Users class="size-4 {activeWorkspace === 'patients' ? 'text-primary' : 'text-muted-foreground'}" />
        <span>Patients Directory</span>
      </button>
      <button
        onclick={() => (activeWorkspace = "appointments")}
        class={cn(
          "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer",
          activeWorkspace === "appointments"
            ? "bg-muted text-foreground font-semibold shadow-xs"
            : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        )}
      >
        <Calendar class="size-4 {activeWorkspace === 'appointments' ? 'text-primary' : 'text-muted-foreground'}" />
        <span>Appointments Schedule</span>
      </button>
    </div>

    <!-- Sidebar Bottom Footer: Unversioned Pre-release Alpha -->
    <div class="p-3 border-t border-border mt-auto">
      <div class="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span class="inline-flex items-center gap-1.5 text-[11px]">
          <span class="size-1.5 rounded-full {isOnline ? 'bg-emerald-500' : 'bg-amber-500'}"></span>
          {isOnline ? "Core Online" : "Connecting..."}
        </span>
        <span class="text-[10px] font-mono text-muted-foreground">Alpha</span>
      </div>
    </div>
  </aside>

  <!-- Right Main Area -->
  <div class="flex-1 flex flex-col h-screen overflow-hidden min-h-0">
    <!-- Top Bar Header -->
    <header class="border-b border-border bg-card/95 backdrop-blur shrink-0 z-40 h-14 flex items-center justify-between px-6 shadow-xs">
      <!-- Breadcrumb / Active Workspace Title -->
      <div class="flex items-center gap-2 text-xs">
        <span class="text-muted-foreground font-normal">Hospital System</span>
        <span class="text-muted-foreground">/</span>
        <span class="font-semibold text-foreground">
          {activeWorkspace === "patients" ? "Patients Directory" : "Appointments Schedule"}
        </span>
      </div>

      <!-- Top Right Controls -->
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <span class="size-2 rounded-full {isOnline ? 'bg-emerald-500' : 'bg-amber-500'}"></span>
          <span>{isOnline ? "Connected" : "Reconnecting..."}</span>
        </span>
      </div>
    </header>

    <!-- Global Error Banner if caught -->
    {#if globalError}
      <div class="bg-destructive/10 border-b border-destructive/20 text-destructive px-6 py-2.5 text-xs flex items-center justify-between shrink-0">
        <span><strong>System Alert:</strong> {globalError}</span>
        <button onclick={() => (globalError = null)} class="text-destructive font-bold underline ml-4 cursor-pointer">
          Dismiss
        </button>
      </div>
    {/if}

    <!-- Main Workspace Content Canvas -->
    <main class="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto flex flex-col overflow-hidden min-h-0">
      {#if activeWorkspace === "patients"}
        <PatientsWorkspace
          bind:isRegisterDialogOpen={triggerPatientRegister}
          onSelectPatientForBooking={handleSelectPatientForBooking}
        />
      {:else if activeWorkspace === "appointments"}
        <AppointmentsWorkspace
          bind:isBookingModalOpen={triggerAppointmentBook}
          preselectedPatient={selectedPatientForBooking}
          onClearPreselectedPatient={handleClearSelectedPatient}
        />
      {/if}
    </main>
  </div>

  <ToastContainer />
</div>
