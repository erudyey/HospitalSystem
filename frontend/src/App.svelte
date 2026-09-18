<script lang="ts">
  import { onMount } from "svelte";
  import {
    api,
    type Patient,
    type StaffUser,
    getUserToken,
    clearUserToken,
  } from "$lib/api";
  import { cn } from "$lib/utils";
  import { toast } from "$lib/toast.svelte";
  import PatientsWorkspace from "./components/PatientsWorkspace.svelte";
  import AppointmentsWorkspace from "./components/AppointmentsWorkspace.svelte";
  import DoctorWorkspace from "./components/DoctorWorkspace.svelte";
  import AuthModal from "./components/AuthModal.svelte";
  import SettingsDialog from "./components/SettingsDialog.svelte";
  import ToastContainer from "$lib/components/ToastContainer.svelte";
  import { Button } from "$lib/components/ui/button";
  import { Badge } from "$lib/components/ui/badge";
  import {
    Users,
    Calendar,
    SquarePlus,
    UserPlus,
    CalendarPlus,
    Stethoscope,
    Shield,
    Settings,
    LogOut,
    Sparkles,
    UserCheck,
    Lock,
    Loader2,
  } from "lucide-svelte";

  type Workspace = "patients" | "appointments" | "doctor_workspace";
  let activeWorkspace = $state<Workspace>("appointments");
  let selectedPatientForBooking = $state<Patient | null>(null);

  let isOnline = $state(false);
  let globalError = $state<string | null>(null);

  // Authentication & Demo State
  let currentUser = $state<StaffUser | null>(null);
  let isAuthChecking = $state(true);
  let isAuthModalOpen = $state(false);
  let isSettingsOpen = $state(false);
  let demoMode = $state(true);

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

  async function initAuth() {
    isAuthChecking = true;
    try {
      // Check stored demo mode preference
      const savedDemo = localStorage.getItem("hospitalsystem_demo_mode");
      if (savedDemo !== null) {
        demoMode = savedDemo === "true";
      }

      // Check current session
      const token = getUserToken();
      if (token) {
        try {
          const res = await api.auth.me();
          currentUser = res.user;
          if (currentUser.role === "doctor") {
            activeWorkspace = "doctor_workspace";
          }
          return;
        } catch {
          clearUserToken();
        }
      }

      // If no valid session and in demo mode, auto-activate receptionist for zero-friction start
      if (demoMode) {
        try {
          const session = await api.auth.login("maria", "password123");
          currentUser = session.user;
          activeWorkspace = "appointments";
        } catch {
          // If demo user is not yet seeded, show modal
          isAuthModalOpen = true;
        }
      } else {
        isAuthModalOpen = true;
      }
    } finally {
      isAuthChecking = false;
    }
  }

  async function switchDemoUser(username: string) {
    try {
      const session = await api.auth.login(username, "password123");
      currentUser = session.user;
      if (currentUser.role === "doctor") {
        activeWorkspace = "doctor_workspace";
      } else {
        activeWorkspace = "appointments";
      }
      toast.success(
        `Switched account to ${currentUser.full_name || currentUser.username} (${currentUser.role}).`
      );
    } catch {
      toast.error("Failed to switch demo account.");
    }
  }

  function handleLogout() {
    clearUserToken();
    currentUser = null;
    if (demoMode) {
      switchDemoUser("maria");
    } else {
      isAuthModalOpen = true;
    }
  }

  onMount(() => {
    checkHealth();
    initAuth();

    // Global Error Boundary listener
    window.addEventListener("error", (event) => {
      globalError = event.message || "An unexpected interface error occurred.";
    });

    window.addEventListener("unhandledrejection", (event) => {
      globalError = event.reason?.message || "An unhandled promise rejection occurred.";
    });

    // Global keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      // Alt+1: Patients, Alt+2: Appointments, Alt+3: Doctor Workspace
      if (e.altKey && e.key === "1") {
        e.preventDefault();
        activeWorkspace = "patients";
      } else if (e.altKey && e.key === "2") {
        e.preventDefault();
        activeWorkspace = currentUser?.role === "doctor" ? "doctor_workspace" : "appointments";
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
    <!-- Clinic Brand Header -->
    <div class="px-4 h-14 border-b border-border flex items-center justify-between">
      <div class="flex items-center gap-2.5">
        <div class="size-7 rounded-lg bg-primary text-primary-foreground flex items-center justify-center shrink-0 shadow-xs">
          <SquarePlus class="size-4" />
        </div>
        <div>
          <h1 class="text-sm font-semibold tracking-tight text-foreground leading-tight">
            Hospital System
          </h1>
          <p class="text-[10px] text-muted-foreground font-medium">Clinical Core</p>
        </div>
      </div>

      <button
        type="button"
        onclick={() => (isSettingsOpen = true)}
        class="size-7 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors cursor-pointer"
        title="Settings & Profile"
      >
        <Settings class="size-4" />
      </button>
    </div>

    <!-- Quick Action CTA Button (Sidebar) -->
    <div class="p-3 border-b border-border">
      {#if currentUser?.role === "doctor"}
        <button
          onclick={() => (activeWorkspace = "doctor_workspace")}
          class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-xs font-medium h-8 px-3 bg-purple-700 text-white shadow-xs hover:bg-purple-800 transition-colors cursor-pointer"
        >
          <Stethoscope class="size-3.5" />
          <span>Physician Triage Queue</span>
        </button>
      {:else}
        <button
          onclick={handleQuickRegisterPatient}
          class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-xs font-medium h-8 px-3 bg-primary text-primary-foreground shadow hover:bg-primary/90 transition-colors cursor-pointer"
        >
          <UserPlus class="size-3.5" />
          <span>+ Register Patient</span>
        </button>
      {/if}
    </div>

    <!-- Navigation Workspace Switcher -->
    <div class="flex-1 py-3 px-2 flex flex-col gap-1 overflow-y-auto">
      <p class="text-[11px] font-medium text-muted-foreground px-2.5 py-1">
        Clinical Modules
      </p>

      {#if currentUser?.role === "doctor"}
        <!-- Doctor Navigation Items -->
        <button
          onclick={() => (activeWorkspace = "doctor_workspace")}
          class={cn(
            "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer",
            activeWorkspace === "doctor_workspace"
              ? "bg-muted text-foreground font-semibold shadow-xs"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          )}
        >
          <Stethoscope class="size-4 {activeWorkspace === 'doctor_workspace' ? 'text-purple-700' : 'text-muted-foreground'}" />
          <span>Doctor Workspace</span>
        </button>

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
          <span>Patient Directory</span>
        </button>

      {:else}
        <!-- Receptionist Navigation Items -->
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
          <span>Appointments & Triage</span>
        </button>

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
      {/if}
    </div>

    <!-- Active User Card (Sidebar Bottom) -->
    <div class="p-3 border-t border-border mt-auto flex flex-col gap-2">
      {#if currentUser}
        <div class="rounded-lg bg-muted/40 p-2 text-xs flex items-center justify-between">
          <div class="flex items-center gap-2 min-w-0">
            <div class="size-6 rounded-full bg-primary/20 text-primary font-bold text-[10px] flex items-center justify-center shrink-0">
              {currentUser.full_name?.charAt(0) || currentUser.username.charAt(0).toUpperCase()}
            </div>
            <div class="min-w-0">
              <p class="font-semibold text-foreground truncate">{currentUser.full_name || currentUser.username}</p>
              <p class="text-[10px] text-muted-foreground capitalize truncate">{currentUser.role}</p>
            </div>
          </div>

          <button
            type="button"
            onclick={() => (isSettingsOpen = true)}
            class="text-muted-foreground hover:text-foreground cursor-pointer p-1"
            title="Profile Settings"
          >
            <Settings class="size-3.5" />
          </button>
        </div>
      {/if}

      <div class="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span class="inline-flex items-center gap-1.5 text-[11px]">
          <span class="size-1.5 rounded-full {isOnline ? 'bg-emerald-500' : 'bg-amber-500'}"></span>
          {isOnline ? "Core Online" : "Connecting..."}
        </span>
        <span class="text-[10px] font-mono text-muted-foreground">SQLite WAL</span>
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
          {#if activeWorkspace === "doctor_workspace"}
            Doctor Workspace (Physician Dashboard)
          {:else if activeWorkspace === "patients"}
            Patients Directory
          {:else}
            Appointments & Front-Desk Triage
          {/if}
        </span>
      </div>

      <!-- Center: 1-Click Passwordless Demo Switcher (if Demo Mode ON) -->
      {#if demoMode}
        <div class="hidden lg:flex items-center gap-1 bg-muted/60 p-1 rounded-lg border border-border/60 text-xs">
          <span class="text-[11px] font-semibold text-muted-foreground px-1.5 flex items-center gap-1">
            <Sparkles class="size-3 text-amber-500" />
            <span>Switch Role:</span>
          </span>

          <button
            type="button"
            onclick={() => switchDemoUser("maria")}
            class={cn(
              "px-2 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer",
              currentUser?.username === "maria"
                ? "bg-primary text-primary-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:bg-background hover:text-foreground"
            )}
          >
            Receptionist
          </button>
          <button
            type="button"
            onclick={() => switchDemoUser("dreyes")}
            class={cn(
              "px-2 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer",
              currentUser?.username === "dreyes"
                ? "bg-purple-700 text-white shadow-2xs font-semibold"
                : "text-muted-foreground hover:bg-background hover:text-foreground"
            )}
          >
            Dr. Reyes
          </button>
          <button
            type="button"
            onclick={() => switchDemoUser("dsantos")}
            class={cn(
              "px-2 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer",
              currentUser?.username === "dsantos"
                ? "bg-purple-700 text-white shadow-2xs font-semibold"
                : "text-muted-foreground hover:bg-background hover:text-foreground"
            )}
          >
            Dr. Santos
          </button>
          <button
            type="button"
            onclick={() => switchDemoUser("dtan")}
            class={cn(
              "px-2 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer",
              currentUser?.username === "dtan"
                ? "bg-purple-700 text-white shadow-2xs font-semibold"
                : "text-muted-foreground hover:bg-background hover:text-foreground"
            )}
          >
            Dr. Tan
          </button>
        </div>
      {/if}

      <!-- Top Right Controls -->
      <div class="flex items-center gap-3">
        {#if currentUser}
          <div class="flex items-center gap-2">
            <Badge
              variant="outline"
              class={cn(
                "text-[11px] font-semibold px-2 py-0.5 capitalize",
                currentUser.role === "doctor"
                  ? "border-purple-300 bg-purple-50 text-purple-800"
                  : "border-sky-300 bg-sky-50 text-sky-800"
              )}
            >
              {currentUser.role}
            </Badge>

            <Button
              variant="ghost"
              size="sm"
              class="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
              onclick={() => (isSettingsOpen = true)}
            >
              Settings
            </Button>
          </div>
        {:else}
          <Button
            size="sm"
            class="h-8 px-3 text-xs cursor-pointer"
            onclick={() => (isAuthModalOpen = true)}
          >
            Sign In
          </Button>
        {/if}
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
      {#if isAuthChecking}
        <div class="flex flex-col items-center justify-center py-24 text-sm text-muted-foreground gap-2">
          <Loader2 class="size-6 animate-spin text-primary" />
          <span>Initializing clinical environment...</span>
        </div>
      {:else if activeWorkspace === "doctor_workspace" && currentUser?.role === "doctor"}
        <DoctorWorkspace activeDoctor={currentUser} />
      {:else if activeWorkspace === "patients"}
        <PatientsWorkspace
          bind:isRegisterDialogOpen={triggerPatientRegister}
          onSelectPatientForBooking={handleSelectPatientForBooking}
        />
      {:else}
        <AppointmentsWorkspace
          bind:isBookingModalOpen={triggerAppointmentBook}
          preselectedPatient={selectedPatientForBooking}
          onClearPreselectedPatient={handleClearSelectedPatient}
        />
      {/if}
    </main>
  </div>

  <!-- Settings & Profile Dialog -->
  <SettingsDialog
    bind:open={isSettingsOpen}
    currentUser={currentUser}
    bind:demoMode={demoMode}
    onProfileUpdated={(updated) => {
      currentUser = updated;
    }}
    onLogout={handleLogout}
  />

  <!-- Auth Gateway Modal -->
  <AuthModal
    bind:open={isAuthModalOpen}
    demoMode={demoMode}
    onSuccess={(user) => {
      currentUser = user;
      if (user.role === "doctor") {
        activeWorkspace = "doctor_workspace";
      } else {
        activeWorkspace = "appointments";
      }
    }}
  />

  <ToastContainer />
</div>
