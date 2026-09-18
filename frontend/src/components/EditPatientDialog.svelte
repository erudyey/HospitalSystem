<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { api, type Patient, type ApiError } from "$lib/api";
  import { Loader2 } from "lucide-svelte";

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

  let fullName = $state("");
  let contact = $state("");
  let age = $state<string | number>("");
  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});

  $effect(() => {
    if (patient && open) {
      fullName = patient.full_name;
      contact = patient.contact || "";
      age = patient.age;
      formErrors = {};
    }
  });

  async function handleSave(e: SubmitEvent) {
    e.preventDefault();
    if (!patient) return;

    formErrors = {};
    const trimmedName = fullName.trim();
    const parsedAge = parseInt(String(age), 10);

    const localErrors: Record<string, string[]> = {};
    if (!trimmedName) localErrors.full_name = ["Full name is required."];
    if (isNaN(parsedAge) || parsedAge <= 0) {
      localErrors.age = ["Age must be a positive whole number greater than 0."];
    }

    if (Object.keys(localErrors).length > 0) {
      formErrors = localErrors;
      return;
    }

    isSubmitting = true;
    try {
      await api.updatePatient(patient.id, {
        full_name: trimmedName,
        contact: contact.trim(),
        age: parsedAge,
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
      <Dialog.Title>Edit Patient Details</Dialog.Title>
      <Dialog.Description>
        Update clinical registration details for patient #{patient?.id}.
      </Dialog.Description>
    </Dialog.Header>

    <form onsubmit={handleSave} class="flex flex-col gap-4 py-2">
      <!-- Full Name -->
      <div>
        <label for="editFullName" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Full Name <span class="text-destructive">*</span>
        </label>
        <Input
          id="editFullName"
          type="text"
          placeholder="e.g. Maria Santos"
          bind:value={fullName}
          aria-invalid={!!formErrors.full_name}
          disabled={isSubmitting}
          autofocus
        />
        {#if formErrors.full_name}
          <p class="text-xs text-destructive mt-1">{formErrors.full_name.join(" ")}</p>
        {/if}
      </div>

      <!-- Contact Number -->
      <div>
        <label for="editContact" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Contact Number <span class="font-normal text-muted-foreground/70 lowercase">(optional)</span>
        </label>
        <Input
          id="editContact"
          type="text"
          placeholder="e.g. 0917-123-4567"
          bind:value={contact}
          aria-invalid={!!formErrors.contact}
          disabled={isSubmitting}
        />
        {#if formErrors.contact}
          <p class="text-xs text-destructive mt-1">{formErrors.contact.join(" ")}</p>
        {/if}
      </div>

      <!-- Age -->
      <div>
        <label for="editAge" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Age <span class="text-destructive">*</span>
        </label>
        <Input
          id="editAge"
          type="number"
          min="1"
          placeholder="e.g. 28"
          bind:value={age}
          aria-invalid={!!formErrors.age}
          disabled={isSubmitting}
        />
        {#if formErrors.age}
          <p class="text-xs text-destructive mt-1">{formErrors.age.join(" ")}</p>
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
