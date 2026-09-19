<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import * as Tabs from "$lib/components/ui/tabs";
  import {
    api,
    type StaffUser,
    type StaffRole,
    type UserSession,
    type ApiError,
  } from "$lib/api";
  import { toast } from "$lib/toast.svelte";
  import {
    ShieldCheck,
    UserCheck,
    Stethoscope,
    Lock,
    KeyRound,
    User,
    Sparkles,
    Loader2,
    AlertCircle,
  } from "lucide-svelte";

  interface Props {
    open?: boolean;
    demoMode?: boolean;
    isSwitchingMode?: boolean;
    onSwitchMode?: () => void;
    onSuccess?: (user: StaffUser) => void;
  }

  let {
    open = $bindable(false),
    demoMode = false,
    isSwitchingMode = false,
    onSwitchMode,
    onSuccess,
  }: Props = $props();

  type AuthTab = "login" | "register";
  let activeTab = $state<AuthTab>("login");

  // Login form
  let loginUsername = $state("");
  let loginPassword = $state("");
  let keepSignedIn = $state(true);

  // Register form
  let regUsername = $state("");
  let regPassword = $state("");
  let regFullName = $state("");
  let regRole = $state<StaffRole>("receptionist");
  let regSpecialty = $state("");
  let regLicenseNumber = $state("");
  let regContact = $state("");

  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});

  // Quick Demo Fill Profiles
  const demoProfiles = [
    {
      username: "maria",
      password: "password123",
      label: "Receptionist (Maria)",
      role: "receptionist",
    },
    {
      username: "dreyes",
      password: "password123",
      label: "Dr. Elena Reyes (General Medicine)",
      role: "doctor",
    },
    {
      username: "dsantos",
      password: "password123",
      label: "Dr. Marco Santos (Pediatrics)",
      role: "doctor",
    },
    {
      username: "dtan",
      password: "password123",
      label: "Dr. Chloe Tan (Cardiology)",
      role: "doctor",
    },
  ];

  function quickFill(profile: (typeof demoProfiles)[0]) {
    loginUsername = profile.username;
    loginPassword = profile.password;
    formErrors = {};
  }

  async function handleLogin(e: SubmitEvent) {
    e.preventDefault();
    formErrors = {};

    const trimmedUser = loginUsername.trim();
    if (!trimmedUser || !loginPassword) {
      formErrors = {
        general: ["Both username and password are required."],
      };
      return;
    }

    isSubmitting = true;
    try {
      const session = await api.auth.login(trimmedUser, loginPassword, keepSignedIn);
      toast.success(`Welcome back, ${session.user.full_name || session.user.username}!`);
      open = false;
      onSuccess?.(session.user);
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }

  async function handleRegister(e: SubmitEvent) {
    e.preventDefault();
    formErrors = {};

    const trimmedUser = regUsername.trim();
    const trimmedName = regFullName.trim();
    if (!trimmedUser || !regPassword || !trimmedName) {
      formErrors = {
        general: ["Username, password, and full name are required."],
      };
      return;
    }

    isSubmitting = true;
    try {
      await api.auth.register({
        username: trimmedUser,
        password: regPassword,
        full_name: trimmedName,
        role: regRole,
        specialty: regSpecialty.trim(),
        license_number: regLicenseNumber.trim(),
        contact: regContact.trim(),
      });

      // Automatically sign in the newly registered staff user to establish session
      const session = await api.auth.login(trimmedUser, regPassword, keepSignedIn);
      toast.success(
        `Staff account created for ${session.user.full_name || session.user.username}!`
      );
      open = false;
      onSuccess?.(session.user);
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-md p-0 overflow-hidden">
    <!-- Modal Header -->
    <div class="px-6 pt-6 pb-4 border-b border-border bg-card">
      <div class="flex items-center gap-2.5">
        <div class="size-8 rounded-lg bg-muted text-foreground flex items-center justify-center">
          <ShieldCheck class="size-4.5 text-muted-foreground" />
        </div>
        <div>
          <Dialog.Title class="text-base font-semibold">
            Hospital System Authentication
          </Dialog.Title>
          <Dialog.Description class="text-xs text-muted-foreground">
            Sign in with your staff account or register new clinical personnel.
          </Dialog.Description>
        </div>
      </div>

      <!-- Tab Switcher -->
      <div class="mt-4">
        <Tabs.Root
          value={activeTab}
          onValueChange={(val) => {
            if (val) {
              activeTab = val as AuthTab;
              formErrors = {};
            }
          }}
        >
          <Tabs.List class="w-full grid grid-cols-2">
            <Tabs.Trigger value="login" class="text-xs">Sign In</Tabs.Trigger>
            <Tabs.Trigger value="register" class="text-xs">Register Staff</Tabs.Trigger>
          </Tabs.List>
        </Tabs.Root>
      </div>
    </div>

    <!-- Modal Body -->
    <div class="px-6 py-4">
      {#if onSwitchMode}
        <div class="mb-4 rounded-lg border border-border p-3">
          <p class="text-xs text-muted-foreground mb-2">
            {demoMode ? "You are using the separate demo database." : "Explore with sample accounts in a separate demo database."}
            The app restarts when switching modes.
          </p>
          <Button type="button" variant="outline" size="sm" class="w-full" disabled={isSubmitting || isSwitchingMode} onclick={onSwitchMode}>
            {isSwitchingMode ? "Switching mode..." : demoMode ? "Return to clinic mode" : "Try demo"}
          </Button>
        </div>
      {/if}
      {#if activeTab === "login"}
        <!-- Demo Mode Quick Fill Chips -->
        {#if demoMode}
          <div class="mb-4 rounded-lg border border-border bg-muted/40 p-3 text-xs">
            <div class="flex items-center gap-1.5 font-medium text-foreground mb-2">
              <Sparkles class="size-3.5 text-muted-foreground" />
              <span>Demo Mode -- Quick Fill Credentials</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {#each demoProfiles as p}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onclick={() => quickFill(p)}
                  class="h-auto py-1.5 px-2.5 justify-between font-normal text-[11px] text-left border bg-background hover:bg-muted/70 cursor-pointer"
                >
                  <span class="font-medium text-foreground truncate">{p.label}</span>
                  <Badge variant="secondary" class="text-[9px] px-1 py-0 uppercase ml-1 shrink-0 font-normal">
                    {p.role}
                  </Badge>
                </Button>
              {/each}
            </div>
          </div>
        {/if}

        <form onsubmit={handleLogin} class="flex flex-col gap-3.5">
          <div>
            <label for="authUsername" class="block text-xs font-medium text-foreground mb-1.5">
              Username
            </label>
            <Input
              id="authUsername"
              type="text"
              placeholder="e.g. maria, dreyes"
              bind:value={loginUsername}
              disabled={isSubmitting}
              class="h-9 text-xs"
              autofocus
            />
          </div>

          <div>
            <label for="authPassword" class="block text-xs font-medium text-foreground mb-1.5">
              Password
            </label>
            <Input
              id="authPassword"
              type="password"
              placeholder="••••••••"
              bind:value={loginPassword}
              disabled={isSubmitting}
              class="h-9 text-xs"
            />
          </div>

          <!-- Keep me signed in option -->
          <div class="flex items-center justify-between py-1">
            <label class="flex items-center gap-2 cursor-pointer select-none text-xs text-foreground font-normal">
              <input
                type="checkbox"
                bind:checked={keepSignedIn}
                class="size-4 rounded border-border text-primary focus:ring-primary/20 accent-primary cursor-pointer"
              />
              <span>Keep me signed in</span>
            </label>
            <span class="text-[11px] text-muted-foreground">Persist session on this PC</span>
          </div>

          {#if formErrors.general}
            <div class="rounded-lg bg-destructive/10 border border-destructive/20 p-2.5 text-xs text-destructive flex items-center gap-2">
              <AlertCircle class="size-4 shrink-0" />
              <span>{formErrors.general.join(" ")}</span>
            </div>
          {/if}

          <div class="pt-1">
            <Button
              type="submit"
              disabled={isSubmitting}
              class="w-full h-9 text-xs font-medium cursor-pointer"
            >
              {#if isSubmitting}
                <Loader2 class="size-3.5 animate-spin mr-1.5" />
              {/if}
              Sign In
            </Button>
          </div>
        </form>

      {:else}
        <!-- Register Form -->
        <form onsubmit={handleRegister} class="flex flex-col gap-3">
          <div class="grid grid-cols-2 gap-2.5">
            <div>
              <label for="regUser" class="block text-xs font-medium text-foreground mb-1">
                Username <span class="text-destructive">*</span>
              </label>
              <Input
                id="regUser"
                type="text"
                placeholder="e.g. jdoe"
                bind:value={regUsername}
                disabled={isSubmitting}
                class="h-8 text-xs"
              />
            </div>
            <div>
              <label for="regPass" class="block text-xs font-medium text-foreground mb-1">
                Password <span class="text-destructive">*</span>
              </label>
              <Input
                id="regPass"
                type="password"
                placeholder="••••••••"
                bind:value={regPassword}
                disabled={isSubmitting}
                class="h-8 text-xs"
              />
            </div>
          </div>

          <div>
            <label for="regName" class="block text-xs font-medium text-foreground mb-1">
              Full Legal Name <span class="text-destructive">*</span>
            </label>
            <Input
              id="regName"
              type="text"
              placeholder="e.g. Dr. Jane Doe / Jane Doe"
              bind:value={regFullName}
              disabled={isSubmitting}
              class="h-8 text-xs"
            />
          </div>

          <div>
            <label for="regRoleSelect" class="block text-xs font-medium text-foreground mb-1">
              Hospital Role <span class="text-destructive">*</span>
            </label>
            <select
              id="regRoleSelect"
              class="h-8 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-xs w-full focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
              bind:value={regRole}
              disabled={isSubmitting}
            >
              <option value="receptionist">Receptionist / Front Desk</option>
              <option value="doctor">Physician / Doctor</option>
            </select>
          </div>

          {#if regRole === "doctor"}
            <div class="grid grid-cols-2 gap-2.5">
              <div>
                <label for="regSpec" class="block text-xs font-medium text-foreground mb-1">
                  Specialty
                </label>
                <Input
                  id="regSpec"
                  type="text"
                  placeholder="e.g. Pediatrics"
                  bind:value={regSpecialty}
                  disabled={isSubmitting}
                  class="h-8 text-xs"
                />
              </div>
              <div>
                <label for="regLic" class="block text-xs font-medium text-foreground mb-1">
                  License #
                </label>
                <Input
                  id="regLic"
                  type="text"
                  placeholder="e.g. PRC-012345"
                  bind:value={regLicenseNumber}
                  disabled={isSubmitting}
                  class="h-8 text-xs"
                />
              </div>
            </div>
          {/if}

          <div>
            <label for="regContact" class="block text-xs font-medium text-foreground mb-1">
              Contact Detail
            </label>
            <Input
              id="regContact"
              type="text"
              placeholder="e.g. +63 917 123 4567"
              bind:value={regContact}
              disabled={isSubmitting}
              class="h-8 text-xs"
            />
          </div>

          {#if formErrors.general}
            <div class="rounded-lg bg-destructive/10 border border-destructive/20 p-2 text-xs text-destructive flex items-center gap-2">
              <AlertCircle class="size-4 shrink-0" />
              <span>{formErrors.general.join(" ")}</span>
            </div>
          {/if}

          <div class="pt-2">
            <Button
              type="submit"
              disabled={isSubmitting}
              class="w-full h-8 text-xs font-medium cursor-pointer"
            >
              {#if isSubmitting}
                <Loader2 class="size-3.5 animate-spin mr-1.5" />
              {/if}
              Register Staff Account
            </Button>
          </div>
        </form>
      {/if}
    </div>
  </Dialog.Content>
</Dialog.Root>
