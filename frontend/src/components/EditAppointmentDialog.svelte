<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { api, type Appointment, type ApiError } from "$lib/api";
  import { Loader2 } from "lucide-svelte";

  interface Props {
    open?: boolean;
    appointment?: Appointment | null;
    onSuccess?: () => void;
  }

  let {
    open = $bindable(false),
    appointment = null,
    onSuccess,
  }: Props = $props();

  let doctorName = $state("");
  let appDate = $state("");
  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});

  $effect(() => {
    if (appointment && open) {
      doctorName = appointment.doctor_name;
      appDate = appointment.app_date;
      formErrors = {};
    }
  });

  async function handleSave(e: SubmitEvent) {
    e.preventDefault();
    if (!appointment) return;

    formErrors = {};
    const trimmedDoctor = doctorName.trim();

    const localErrors: Record<string, string[]> = {};
    if (!trimmedDoctor) localErrors.doctor_name = ["Doctor name is required."];
    if (!appDate) localErrors.app_date = ["Appointment date is required."];

    if (Object.keys(localErrors).length > 0) {
      formErrors = localErrors;
      return;
    }

    isSubmitting = true;
    try {
      await api.updateAppointment(appointment.id, {
        doctor_name: trimmedDoctor,
        app_date: appDate,
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
        Update the attending doctor or consultation date for {appointment?.patient_name}.
      </Dialog.Description>
    </Dialog.Header>

    <form onsubmit={handleSave} class="flex flex-col gap-4 py-2">
      <!-- Attending Doctor -->
      <div>
        <label for="editDoctor" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Attending Doctor <span class="text-destructive">*</span>
        </label>
        <Input
          id="editDoctor"
          type="text"
          placeholder="e.g. Dr. Maria Cruz"
          bind:value={doctorName}
          aria-invalid={!!formErrors.doctor_name}
          disabled={isSubmitting}
          autofocus
        />
        {#if formErrors.doctor_name}
          <p class="text-xs text-destructive mt-1">{formErrors.doctor_name.join(" ")}</p>
        {/if}
      </div>

      <!-- Consultation Date -->
      <div>
        <label for="editDate" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Consultation Date <span class="text-destructive">*</span>
        </label>
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
        <Button type="submit" disabled={isSubmitting}>
          {#if isSubmitting}
            <Loader2 class="size-4 mr-2 animate-spin" />
          {/if}
          Save Changes
        </Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
