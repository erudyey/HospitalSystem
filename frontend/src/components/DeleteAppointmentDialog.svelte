<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { api, type Appointment, type ApiError } from "$lib/api";
  import { AlertTriangle, Loader2 } from "lucide-svelte";

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

  let isDeleting = $state(false);
  let errorMessage = $state<string | null>(null);

  async function handleDelete() {
    if (!appointment) return;
    isDeleting = true;
    errorMessage = null;

    try {
      await api.deleteAppointment(appointment.id);
      open = false;
      onSuccess?.();
    } catch (err) {
      const e = err as ApiError;
      errorMessage = e.message || "Failed to delete appointment.";
    } finally {
      isDeleting = false;
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2 text-destructive">
        <AlertTriangle class="size-5 shrink-0" />
        <span>Delete Appointment</span>
      </Dialog.Title>
      <Dialog.Description>
        This action cannot be undone. Are you sure you want to permanently delete appointment
        <strong class="text-foreground">#{appointment?.id}</strong> for
        <strong class="text-foreground">{appointment?.patient_name}</strong> with
        {appointment?.doctor_name} on {appointment?.app_date}?
      </Dialog.Description>
    </Dialog.Header>

    {#if errorMessage}
      <div class="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
        {errorMessage}
      </div>
    {/if}

    <Dialog.Footer class="pt-2">
      <Button
        type="button"
        variant="outline"
        onclick={() => (open = false)}
        disabled={isDeleting}
      >
        Cancel
      </Button>
      <Button
        type="button"
        variant="destructive"
        onclick={handleDelete}
        disabled={isDeleting}
      >
        {#if isDeleting}
          <Loader2 class="size-4 mr-2 animate-spin" />
        {/if}
        Confirm Delete
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
