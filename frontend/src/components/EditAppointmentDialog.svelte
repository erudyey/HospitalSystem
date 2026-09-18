<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import {
    api,
    type Appointment,
    type StaffUser,
    type ApiError,
  } from "$lib/api";
  import { Loader2, AlertTriangle } from "lucide-svelte";

  interface Props {
    open?: boolean;
    appointment?: Appointment | null;
    doctorList?: StaffUser[];
    onSuccess?: () => void;
  }

  let {
    open = $bindable(false),
    appointment = null,
    doctorList = [],
    onSuccess,
  }: Props = $props();

  let selectedDoctorId = $state<number | null>(null);
  let doctorName = $state("");
  let appDate = $state("");
  let appTime = $state("09:00");
  let reasonForVisit = $state("");

  let conflictWarning = $state<string | null>(null);
  let isCheckingConflict = $state(false);
  let overrideConflict = $state(false);
  let conflictCheckTimer: ReturnType<typeof setTimeout> | null = null;

  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});

  function formatTime(timeStr?: string): string {
    if (!timeStr) return "--:--";
    const parts = timeStr.split(":");
    if (parts.length < 2) return timeStr;
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return timeStr;
    const ampm = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 || 12;
    const mm = m.toString().padStart(2, "0");
    return `${h12}:${mm} ${ampm}`;
  }

  $effect(() => {
    if (appointment && open) {
      selectedDoctorId = appointment.doctor_id ?? null;
      doctorName = appointment.doctor_name || "";
      appDate = appointment.app_date;
      appTime = appointment.app_time || "09:00";
      reasonForVisit = appointment.reason_for_visit || "";
      conflictWarning = null;
      overrideConflict = false;
      formErrors = {};
    }
  });

  function runConflictCheck() {
    if (conflictCheckTimer) clearTimeout(conflictCheckTimer);
    conflictWarning = null;
    if (!selectedDoctorId || selectedDoctorId <= 0 || !appDate || !appTime || !appointment) {
      isCheckingConflict = false;
      return;
    }

    isCheckingConflict = true;
    conflictCheckTimer = setTimeout(async () => {
      try {
        if (!selectedDoctorId || selectedDoctorId <= 0 || !appointment) return;
        const res = await api.clinical.checkScheduleConflict(
          selectedDoctorId,
          appDate,
          appTime,
          appointment.id
        );
        if (res.has_conflict && res.conflicts.length > 0) {
          const first = res.conflicts[0];
          const doc = doctorList.find((d) => d.id === selectedDoctorId);
          const docDisplayName = doc ? doc.full_name : doctorName || "Doctor";
          const formattedTime = formatTime(first.app_time);
          conflictWarning = `${docDisplayName} already has an active appointment (#${first.id} with ${first.patient_name} at ${formattedTime}) within +/- 15 minutes.`;
        } else {
          conflictWarning = null;
          overrideConflict = false;
        }
      } catch {
        // Non-blocking conflict check failure
      } finally {
        isCheckingConflict = false;
      }
    }, 250);
  }

  $effect(() => {
    if (open && appointment && selectedDoctorId && appDate && appTime) {
      runConflictCheck();
    }
  });

  function setQuickDate(daysOffset: number) {
    const d = new Date();
    d.setDate(d.getDate() + daysOffset);
    appDate = d.toISOString().split("T")[0];
  }

  async function handleSave(e: SubmitEvent) {
    e.preventDefault();
    if (!appointment) return;

    formErrors = {};
    const trimmedDoctor = doctorName.trim();

    const localErrors: Record<string, string[]> = {};
    if (!trimmedDoctor && (!selectedDoctorId || selectedDoctorId <= 0)) {
      localErrors.doctor_name = ["Attending doctor is required."];
    }
    if (!appDate) localErrors.app_date = ["Appointment date is required."];
    if (!appTime) localErrors.app_time = ["Appointment time is required."];

    if (conflictWarning && !overrideConflict) {
      localErrors.general = [
        "Schedule conflict detected. Check 'Emergency / Reschedule Override' to proceed.",
      ];
    }

    if (Object.keys(localErrors).length > 0) {
      formErrors = localErrors;
      return;
    }

    isSubmitting = true;
    try {
      await api.updateAppointment(appointment.id, {
        doctor_id: selectedDoctorId && selectedDoctorId > 0 ? selectedDoctorId : null,
        doctor_name: trimmedDoctor || (doctorList.find((d) => d.id === selectedDoctorId)?.full_name ?? "Attending Physician"),
        app_date: appDate,
        app_time: appTime,
        reason_for_visit: reasonForVisit.trim(),
      });
      open = false;
      onSuccess?.();
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Reschedule Appointment #{appointment?.id}</Dialog.Title>
      <Dialog.Description>
        Update the attending doctor, consultation date, or time for {appointment?.patient_name}.
      </Dialog.Description>
    </Dialog.Header>

    <form onsubmit={handleSave} class="flex flex-col gap-4 py-2">
      <!-- Attending Doctor -->
      <div>
        <label for="editDoctorSelect" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Attending Physician <span class="text-destructive">*</span>
        </label>
        <select
          id="editDoctorSelect"
          class="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm w-full focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
          bind:value={selectedDoctorId}
          onchange={(e) => {
            const val = Number((e.target as HTMLSelectElement).value);
            selectedDoctorId = val > 0 ? val : null;
            if (val > 0) {
              const doc = doctorList.find((d) => d.id === val);
              if (doc) doctorName = doc.full_name;
            } else if (val === -1) {
              doctorName = "";
            }
          }}
          disabled={isSubmitting}
        >
          {#if doctorList.length > 0}
            <option value={null}>-- Select Attending Physician --</option>
            {#each doctorList as doc (doc.id)}
              <option value={doc.id}>
                Dr. {doc.full_name.replace(/^Dr\.\s*/i, "")} ({doc.specialty || "General Medicine"})
              </option>
            {/each}
            <option value={-1}>Other / Visiting Physician...</option>
          {:else}
            <option value={null}>No registered physicians found</option>
            <option value={-1}>Custom Physician Name...</option>
          {/if}
        </select>

        {#if selectedDoctorId === -1 || doctorList.length === 0}
          <div class="mt-2">
            <Input
              id="editDoctorCustom"
              type="text"
              placeholder="e.g. Dr. Maria Cruz"
              bind:value={doctorName}
              aria-invalid={!!formErrors.doctor_name}
              disabled={isSubmitting}
            />
          </div>
        {/if}

        {#if formErrors.doctor_name}
          <p class="text-xs text-destructive mt-1">{formErrors.doctor_name.join(" ")}</p>
        {/if}
      </div>

      <!-- Consultation Date & Time -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label for="editDate" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Date <span class="text-destructive">*</span>
            </label>
            <div class="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="h-6 text-[11px] px-1 text-muted-foreground hover:text-foreground cursor-pointer"
                onclick={() => setQuickDate(0)}
              >
                Today
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="h-6 text-[11px] px-1 text-muted-foreground hover:text-foreground cursor-pointer"
                onclick={() => setQuickDate(1)}
              >
                Tomorrow
              </Button>
            </div>
          </div>
          <Input
            id="editDate"
            type="date"
            bind:value={appDate}
            aria-invalid={!!formErrors.app_date}
            disabled={isSubmitting}
          />
          {#if formErrors.app_date}
            <p class="text-xs text-destructive mt-1">{formErrors.app_date.join(" ")}</p>
          {/if}
        </div>

        <div>
          <label for="editTime" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            Time Slot <span class="text-destructive">*</span>
          </label>
          <Input
            id="editTime"
            type="time"
            bind:value={appTime}
            aria-invalid={!!formErrors.app_time}
            disabled={isSubmitting}
          />
          {#if formErrors.app_time}
            <p class="text-xs text-destructive mt-1">{formErrors.app_time.join(" ")}</p>
          {/if}
        </div>
      </div>

      <!-- Reason for Visit -->
      <div>
        <label for="editReason" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Reason for Visit
        </label>
        <Input
          id="editReason"
          type="text"
          placeholder="e.g. Routine checkup, throat pain"
          bind:value={reasonForVisit}
          disabled={isSubmitting}
        />
      </div>

      <!-- Reactive Conflict Check Warning Banner -->
      {#if isCheckingConflict}
        <div class="flex items-center gap-2 text-xs text-muted-foreground py-1">
          <Loader2 class="size-3 animate-spin text-primary" />
          <span>Checking doctor schedule availability...</span>
        </div>
      {:else if conflictWarning}
        <div class="rounded-lg border border-amber-300 bg-amber-50/90 p-3 text-xs text-amber-900 flex flex-col gap-2">
          <div class="flex items-center gap-2 font-semibold text-amber-800">
            <AlertTriangle class="size-4 text-amber-600 shrink-0" />
            <span>Schedule Conflict Warning</span>
          </div>
          <p>{conflictWarning}</p>
          <label class="flex items-center gap-2 font-medium cursor-pointer text-amber-950 mt-1 select-none">
            <input
              type="checkbox"
              bind:checked={overrideConflict}
              class="rounded border-amber-400 text-amber-600 focus:ring-amber-500 cursor-pointer"
            />
            <span>Emergency / Reschedule Override (Save Anyway)</span>
          </label>
        </div>
      {/if}

      {#if formErrors.general}
        <div class="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
          {formErrors.general.join(" ")}
        </div>
      {/if}

      <Dialog.Footer class="pt-2">
        <Button
          type="button"
          variant="outline"
          onclick={() => (open = false)}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting || (!!conflictWarning && !overrideConflict)}
          class="cursor-pointer"
        >
          {#if isSubmitting}
            <Loader2 class="size-4 mr-2 animate-spin" />
          {/if}
          Save Changes
        </Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
