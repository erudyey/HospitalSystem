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

      // Check if user explicitly logged out in this session
      let hasExplicitLogout = false;
      try {
        hasExplicitLogout = sessionStorage.getItem("hospitalsystem_explicit_logout") === "true";
      } catch {
        // Ignore storage restrictions
      }

      // If no valid session and in demo mode AND user did not explicitly log out,
      // auto-activate receptionist for zero-friction start
      if (demoMode && !hasExplicitLogout) {
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
      try {
        sessionStorage.removeItem("hospitalsystem_explicit_logout");
      } catch {
        // Ignore storage restrictions
      }
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
    try {
      sessionStorage.setItem("hospitalsystem_explicit_logout", "true");
    } catch {
      // Ignore storage restrictions
    }
    isAuthModalOpen = true;
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

      <Button
        type="button"
        variant="ghost"
        size="icon"
        onclick={() => (isSettingsOpen = true)}
        class="size-7 text-muted-foreground hover:text-foreground cursor-pointer"
        title="Settings & Profile"
      >
        <Settings class="size-4" />
      </Button>
    </div>

    <!-- Quick Action CTA Button (Sidebar) -->
    <div class="p-3 border-b border-border">
      {#if currentUser?.role === "doctor"}
        <Button
          variant="secondary"
          size="sm"
          onclick={() => (activeWorkspace = "doctor_workspace")}
          class="w-full justify-center gap-2 text-xs font-medium cursor-pointer shadow-xs"
        >
          <Stethoscope class="size-3.5" />
          <span>Physician Triage Queue</span>
        </Button>
      {:else}
        <Button
          variant="default"
          size="sm"
          onclick={handleQuickRegisterPatient}
          class="w-full justify-center gap-2 text-xs font-medium cursor-pointer shadow-xs"
        >
          <UserPlus class="size-3.5" />
          <span>+ Register Patient</span>
        </Button>
      {/if}
    </div>

    <!-- Navigation Workspace Switcher -->
    <div class="flex-1 py-3 px-2 flex flex-col gap-1 overflow-y-auto">
      <p class="text-[11px] font-medium text-muted-foreground px-2.5 py-1">
        Clinical Modules
      </p>

      {#if currentUser?.role === "doctor"}
        <!-- Doctor Navigation Items -->
        <Button
          variant={activeWorkspace === "doctor_workspace" ? "secondary" : "ghost"}
          size="sm"
          onclick={() => (activeWorkspace = "doctor_workspace")}
          class="w-full justify-start gap-2.5 px-2.5 h-9 text-xs cursor-pointer {activeWorkspace === 'doctor_workspace' ? 'font-semibold text-foreground shadow-2xs' : 'text-muted-foreground'}"
        >
          <Stethoscope class="size-4 shrink-0 {activeWorkspace === 'doctor_workspace' ? 'text-primary' : 'text-muted-foreground'}" />
          <span>Doctor Workspace</span>
        </Button>

        <Button
          variant={activeWorkspace === "patients" ? "secondary" : "ghost"}
          size="sm"
          onclick={() => (activeWorkspace = "patients")}
          class="w-full justify-start gap-2.5 px-2.5 h-9 text-xs cursor-pointer {activeWorkspace === 'patients' ? 'font-semibold text-foreground shadow-2xs' : 'text-muted-foreground'}"
        >
          <Users class="size-4 shrink-0 {activeWorkspace === 'patients' ? 'text-primary' : 'text-muted-foreground'}" />
          <span>Patient Directory</span>
        </Button>

      {:else}
        <!-- Receptionist Navigation Items -->
        <Button
          variant={activeWorkspace === "appointments" ? "secondary" : "ghost"}
          size="sm"
          onclick={() => (activeWorkspace = "appointments")}
          class="w-full justify-start gap-2.5 px-2.5 h-9 text-xs cursor-pointer {activeWorkspace === 'appointments' ? 'font-semibold text-foreground shadow-2xs' : 'text-muted-foreground'}"
        >
          <Calendar class="size-4 shrink-0 {activeWorkspace === 'appointments' ? 'text-primary' : 'text-muted-foreground'}" />
          <span>Appointments & Triage</span>
        </Button>

        <Button
          variant={activeWorkspace === "patients" ? "secondary" : "ghost"}
          size="sm"
          onclick={() => (activeWorkspace = "patients")}
          class="w-full justify-start gap-2.5 px-2.5 h-9 text-xs cursor-pointer {activeWorkspace === 'patients' ? 'font-semibold text-foreground shadow-2xs' : 'text-muted-foreground'}"
        >
          <Users class="size-4 shrink-0 {activeWorkspace === 'patients' ? 'text-primary' : 'text-muted-foreground'}" />
          <span>Patients Directory</span>
        </Button>
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

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onclick={() => (isSettingsOpen = true)}
            class="size-6 text-muted-foreground hover:text-foreground cursor-pointer"
            title="Profile Settings"
          >
            <Settings class="size-3.5" />
          </Button>
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
        <div class="hidden lg:flex items-center gap-1 bg-muted/70 p-1 rounded-lg border border-border/60 text-xs">
          <span class="text-[11px] font-semibold text-muted-foreground px-1.5 flex items-center gap-1">
            <Sparkles class="size-3 text-primary" />
            <span>Switch Role:</span>
          </span>

          <Button
            type="button"
            variant={currentUser?.username === "maria" ? "default" : "ghost"}
            size="sm"
            onclick={() => switchDemoUser("maria")}
            class="h-7 px-2.5 text-xs font-medium cursor-pointer"
          >
            Receptionist
          </Button>
          <Button
            type="button"
            variant={currentUser?.username === "dreyes" ? "default" : "ghost"}
            size="sm"
            onclick={() => switchDemoUser("dreyes")}
            class="h-7 px-2.5 text-xs font-medium cursor-pointer"
          >
            Dr. Reyes
          </Button>
          <Button
            type="button"
            variant={currentUser?.username === "dsantos" ? "default" : "ghost"}
            size="sm"
            onclick={() => switchDemoUser("dsantos")}
            class="h-7 px-2.5 text-xs font-medium cursor-pointer"
          >
            Dr. Santos
          </Button>
          <Button
            type="button"
            variant={currentUser?.username === "dtan" ? "default" : "ghost"}
            size="sm"
            onclick={() => switchDemoUser("dtan")}
            class="h-7 px-2.5 text-xs font-medium cursor-pointer"
          >
            Dr. Tan
          </Button>
        </div>
      {/if}

      <!-- Top Right Controls -->
      <div class="flex items-center gap-3">
        {#if currentUser}
          <div class="flex items-center gap-2">
            <Badge
              variant={currentUser.role === "doctor" ? "default" : "secondary"}
              class="text-[11px] font-semibold px-2 py-0.5 capitalize"
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
        <Button
          variant="ghost"
          size="sm"
          onclick={() => (globalError = null)}
          class="h-6 text-destructive font-semibold hover:bg-destructive/10 px-2 cursor-pointer"
        >
          Dismiss
        </Button>
      </div>
    {/if}

    <!-- Main Workspace Content Canvas -->
    <main class="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto flex flex-col overflow-hidden min-h-0">
      {#if isAuthChecking}
        <div class="flex flex-col items-center justify-center py-24 text-sm text-muted-foreground gap-2">
          <Loader2 class="size-6 animate-spin text-primary" />
          <span>Initializing clinical environment...</span>
        </div>
      {:else if !currentUser}
        <div class="flex-1 flex flex-col items-center justify-center text-center p-8">
          <div class="size-12 rounded-xl bg-muted flex items-center justify-center mb-3">
            <Shield class="size-6 text-muted-foreground" />
          </div>
          <h3 class="text-base font-semibold text-foreground">Staff Authentication Required</h3>
          <p class="text-xs text-muted-foreground max-w-sm mt-1 mb-4">
            Please sign in with your receptionist or physician credentials to access clinical records and scheduling.
          </p>
          <Button size="sm" onclick={() => (isAuthModalOpen = true)} class="cursor-pointer">
            Sign In to Clinical Core
          </Button>
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
      try {
        sessionStorage.removeItem("hospitalsystem_explicit_logout");
      } catch {
        // Ignore storage restrictions
      }
      if (user.role === "doctor") {
        activeWorkspace = "doctor_workspace";
      } else {
        activeWorkspace = "appointments";
      }
    }}
  />

  <ToastContainer />
</div>
