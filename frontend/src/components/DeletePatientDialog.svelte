<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { api, type Patient, type ApiError } from "$lib/api";
  import { AlertTriangle, Loader2 } from "lucide-svelte";

  interface Props {
    open?: boolean;
    patient?: Patient | null;
    onSuccess?: () => void;
  }

  let {
    open = $bindable(false),
    patient = null,
    onSuccess,
  }: Props = $props();

  let isDeleting = $state(false);
  let errorMessage = $state<string | null>(null);

  async function handleDelete() {
    if (!patient) return;
    isDeleting = true;
    errorMessage = null;

    try {
      await api.deletePatient(patient.id);
      open = false;
      onSuccess?.();
    } catch (err) {
      const e = err as ApiError;
      errorMessage = e.message || "Failed to delete patient record.";
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
        <span>Delete Patient Record</span>
      </Dialog.Title>
      <Dialog.Description>
        This action cannot be undone. You are about to delete the clinical record for
        <strong class="text-foreground">{patient?.full_name}</strong> (ID #{patient?.id}).
      </Dialog.Description>
    </Dialog.Header>

    {#if patient && (patient.appointment_count ?? 0) > 0}
      <div class="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive flex flex-col gap-1">
        <p class="font-semibold">Cascade Deletion Warning</p>
        <p>
          This patient has {patient.appointment_count} active or historical appointment record(s).
          Deleting this patient will permanently remove all associated consultations from the database.
        </p>
      </div>
    {/if}

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
