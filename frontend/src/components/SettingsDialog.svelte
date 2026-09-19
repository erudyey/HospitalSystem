<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import * as Tabs from "$lib/components/ui/tabs";
  import {
    api,
    type StaffUser,
    type ApiError,
  } from "$lib/api";
  import { toast } from "$lib/toast.svelte";
  import {
    Settings,
    User,
    Shield,
    Database,
    LogOut,
    KeyRound,
    Sparkles,
    CheckCircle2,
    Loader2,
    AlertCircle,
  } from "lucide-svelte";

  interface Props {
    open?: boolean;
    currentUser?: StaffUser | null;
    demoMode?: boolean;
    initialTab?: "profile" | "system";
    onProfileUpdated?: (user: StaffUser) => void;
    onLogout?: () => void;
    onOpenAuth?: () => void;
  }

  let {
    open = $bindable(false),
    currentUser = null,
    demoMode = $bindable(true),
    initialTab = "profile",
    onProfileUpdated,
    onLogout,
    onOpenAuth,
  }: Props = $props();

  type SettingsTab = "profile" | "system";
  let activeTab = $state<SettingsTab>("profile");

  // Profile Form State
  let fullName = $state("");
  let contact = $state("");
  let specialty = $state("");
  let licenseNumber = $state("");
  let newPassword = $state("");
  let confirmPassword = $state("");

  let isSaving = $state(false);
  let isLoggingOut = $state(false);
  let formErrors = $state<Record<string, string[]>>({});

  $effect(() => {
    if (open) {
      if (!currentUser) {
        activeTab = "system";
      } else {
        activeTab = initialTab || "profile";
        fullName = currentUser.full_name || "";
        contact = currentUser.contact || "";
        specialty = currentUser.specialty || "";
        licenseNumber = currentUser.license_number || "";
        newPassword = "";
        confirmPassword = "";
        formErrors = {};
      }
    }
  });

  function toggleDemoMode() {
    demoMode = !demoMode;
    try {
      localStorage.setItem("hospitalsystem_demo_mode", demoMode ? "true" : "false");
    } catch {
      // Ignore storage restrictions
    }
    toast.success(
      demoMode
        ? "Demo Mode enabled -- 1-click role switchers active."
        : "Production Mode active -- Demo switchers hidden."
    );
  }

  async function handleSaveProfile(e: SubmitEvent) {
    e.preventDefault();
    formErrors = {};

    if (newPassword && newPassword.length < 6) {
      formErrors = {
        password: ["New password must be at least 6 characters long."],
      };
      return;
    }

    if (newPassword && newPassword !== confirmPassword) {
      formErrors = {
        password: ["Password confirmation does not match."],
      };
      return;
    }

    isSaving = true;
    try {
      const updated = await api.auth.updateProfile({
        full_name: fullName.trim(),
        contact: contact.trim(),
        specialty: specialty.trim(),
        license_number: licenseNumber.trim(),
        new_password: newPassword || undefined,
      });

      toast.success("Profile updated successfully.");
      onProfileUpdated?.((updated as any).user || updated);
      newPassword = "";
      confirmPassword = "";
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSaving = false;
    }
  }

  async function handleLogout() {
    isLoggingOut = true;
    try {
      await api.auth.logout();
    } catch {
      // Clear client session even if API call fails
    } finally {
      isLoggingOut = false;
      open = false;
      toast.success("Signed out successfully.");
      onLogout?.();
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-lg p-0 overflow-hidden">
    <!-- Header -->
    <div class="px-6 pt-6 pb-4 border-b border-border bg-card">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <div class="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Settings class="size-4.5" />
          </div>
          <div>
            <Dialog.Title class="text-base font-semibold">
              {currentUser ? "System Settings & Profile" : "System Settings"}
            </Dialog.Title>
            <Dialog.Description class="text-xs text-muted-foreground">
              {currentUser
                ? "Manage your staff credentials and runtime configuration."
                : "Runtime configuration and database status."}
            </Dialog.Description>
          </div>
        </div>

        <Badge variant={currentUser ? "outline" : "secondary"} class="text-xs capitalize font-medium">
          {currentUser ? currentUser.role : "Guest"}
        </Badge>
      </div>

      <!-- Tab Navigation (only when logged in with profile) -->
      {#if currentUser}
        <div class="mt-4">
          <Tabs.Root
            value={activeTab}
            onValueChange={(val) => {
              if (val) activeTab = val as SettingsTab;
            }}
          >
            <Tabs.List class="w-full grid grid-cols-2">
              <Tabs.Trigger value="profile" class="text-xs gap-1.5">
                <User class="size-3.5" />
                <span>Staff Profile</span>
              </Tabs.Trigger>
              <Tabs.Trigger value="system" class="text-xs gap-1.5">
                <Database class="size-3.5" />
                <span>System & Demo Mode</span>
              </Tabs.Trigger>
            </Tabs.List>
          </Tabs.Root>
        </div>
      {/if}
    </div>

    <!-- Body -->
    <div class="px-6 py-4">
      {#if activeTab === "profile"}
        <form onsubmit={handleSaveProfile} class="flex flex-col gap-3.5">
          <div class="grid grid-cols-2 gap-2.5">
            <div>
              <label for="profUser" class="block text-xs font-medium text-foreground mb-1">
                Username
              </label>
              <Input
                id="profUser"
                type="text"
                value={currentUser?.username || ""}
                disabled
                class="h-8 text-xs bg-muted/50 cursor-not-allowed"
              />
            </div>
            <div>
              <label for="profName" class="block text-xs font-medium text-foreground mb-1">
                Full Name
              </label>
              <Input
                id="profName"
                type="text"
                bind:value={fullName}
                disabled={isSaving}
                class="h-8 text-xs"
              />
            </div>
          </div>

          {#if currentUser?.role === "doctor"}
            <div class="grid grid-cols-2 gap-2.5">
              <div>
                <label for="profSpec" class="block text-xs font-medium text-foreground mb-1">
                  Specialty
                </label>
                <Input
                  id="profSpec"
                  type="text"
                  bind:value={specialty}
                  disabled={isSaving}
                  class="h-8 text-xs"
                />
              </div>
              <div>
                <label for="profLic" class="block text-xs font-medium text-foreground mb-1">
                  License Number
                </label>
                <Input
                  id="profLic"
                  type="text"
                  bind:value={licenseNumber}
                  disabled={isSaving}
                  class="h-8 text-xs"
                />
              </div>
            </div>
          {/if}

          <div>
            <label for="profContact" class="block text-xs font-medium text-foreground mb-1">
              Contact Details
            </label>
            <Input
              id="profContact"
              type="text"
              bind:value={contact}
              disabled={isSaving}
              class="h-8 text-xs"
            />
          </div>

          <!-- Password Change Section -->
          <div class="pt-2 border-t border-border/80 flex flex-col gap-2.5">
            <p class="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <KeyRound class="size-3.5 text-primary" />
              <span>Change Password (optional)</span>
            </p>
            <div class="grid grid-cols-2 gap-2.5">
              <Input
                type="password"
                placeholder="New password"
                bind:value={newPassword}
                disabled={isSaving}
                class="h-8 text-xs"
              />
              <Input
                type="password"
                placeholder="Confirm password"
                bind:value={confirmPassword}
                disabled={isSaving}
                class="h-8 text-xs"
              />
            </div>
          </div>

          {#if formErrors.general || formErrors.password}
            <div class="rounded-lg bg-destructive/10 border border-destructive/20 p-2 text-xs text-destructive flex items-center gap-2">
              <AlertCircle class="size-4 shrink-0" />
              <span>{(formErrors.general || formErrors.password)?.join(" ")}</span>
            </div>
          {/if}

          <div class="pt-2 flex justify-end">
            <Button
              type="submit"
              disabled={isSaving}
              size="sm"
              class="h-8 text-xs cursor-pointer"
            >
              {#if isSaving}
                <Loader2 class="size-3.5 animate-spin mr-1.5" />
              {/if}
              Save Profile Changes
            </Button>
          </div>
        </form>

      {:else}
        <!-- System & Demo Mode Tab -->
        <div class="flex flex-col gap-4">
          <!-- Demo Mode Toggle Card -->
          <div class="rounded-xl border border-primary/20 bg-primary/5 p-4 flex items-start justify-between gap-4">
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-2">
                <Sparkles class="size-4 text-primary" />
                <h4 class="text-xs font-semibold text-foreground">Evaluation Demo Mode</h4>
                <Badge variant="outline" class="text-[10px] px-1.5 py-0 {demoMode ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-zinc-100 text-zinc-600'}">
                  {demoMode ? "ACTIVE" : "OFF"}
                </Badge>
              </div>
              <p class="text-xs text-muted-foreground leading-relaxed">
                When enabled, 1-click role switchers appear in the top bar to effortlessly switch between Receptionist, Dr. Reyes, Dr. Santos, and Dr. Tan without entering passwords.
              </p>
            </div>

            <Button
              type="button"
              variant={demoMode ? "default" : "outline"}
              size="sm"
              class="h-8 text-xs shrink-0 cursor-pointer"
              onclick={toggleDemoMode}
            >
              {demoMode ? "Turn Off" : "Enable Demo"}
            </Button>
          </div>

          <!-- Storage & Engine Info -->
          <div class="rounded-xl border border-border bg-card p-4 flex flex-col gap-2.5 text-xs">
            <div class="flex items-center gap-2 font-semibold text-foreground">
              <Database class="size-4 text-muted-foreground" />
              <span>Database Architecture & Storage</span>
            </div>

            <div class="flex flex-col gap-1.5 text-muted-foreground">
              <div class="flex justify-between">
                <span>Engine:</span>
                <span class="font-mono text-foreground">SQLite 3 (WAL Mode)</span>
              </div>
              <div class="flex justify-between">
                <span>Multi-reader concurrency:</span>
                <span class="font-mono text-emerald-700 font-semibold">Active</span>
              </div>
              <div class="flex justify-between">
                <span>Busy timeout:</span>
                <span class="font-mono text-foreground">20,000 ms</span>
              </div>
              <div class="flex justify-between">
                <span>Foreign key enforcement:</span>
                <span class="font-mono text-emerald-700 font-semibold">PRAGMA foreign_keys = ON</span>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <div class="px-6 py-3 border-t border-border bg-card flex items-center justify-between">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onclick={() => (open = false)}
        class="text-xs cursor-pointer"
      >
        Close
      </Button>

      {#if currentUser}
        <Button
          type="button"
          variant="destructive"
          size="sm"
          onclick={handleLogout}
          disabled={isLoggingOut}
          class="h-8 text-xs cursor-pointer gap-1.5"
        >
          {#if isLoggingOut}
            <Loader2 class="size-3.5 animate-spin" />
          {:else}
            <LogOut class="size-3.5" />
          {/if}
          Log Out Staff Session
        </Button>
      {:else}
        <Button
          type="button"
          size="sm"
          onclick={() => {
            open = false;
            onOpenAuth?.();
          }}
          class="h-8 text-xs cursor-pointer gap-1.5"
        >
          Sign In to Staff Account
        </Button>
      {/if}
    </div>
  </Dialog.Content>
</Dialog.Root>
