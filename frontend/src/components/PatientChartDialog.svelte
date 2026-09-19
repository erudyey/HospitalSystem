<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Badge } from "$lib/components/ui/badge";
  import {
    api,
    type Patient,
    type MedicalRecord,
    type ApiError,
  } from "$lib/api";
  import {
    FileText,
    Clock,
    Pill,
    Stethoscope,
    Calendar,
    User,
    RefreshCw,
    X,
  } from "lucide-svelte";

  interface Props {
    open?: boolean;
    patient?: Patient | null;
  }

  let {
    open = $bindable(false),
    patient = null,
  }: Props = $props();

  let records = $state<MedicalRecord[]>([]);
  let isLoading = $state(false);
  let errorMessage = $state<string | null>(null);

  function formatDate(isoStr: string): string {
    if (!isoStr) return "";
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoStr;
    }
  }

  async function loadHistory() {
    if (!patient) return;
    isLoading = true;
    errorMessage = null;
    try {
      records = await api.clinical.getPatientMedicalHistory(patient.id);
    } catch (err) {
      const e = err as ApiError;
      errorMessage = e.message || "Failed to load patient medical history.";
    } finally {
      isLoading = false;
    }
  }

  $effect(() => {
    if (open && patient) {
      loadHistory();
    } else if (!open) {
      records = [];
      errorMessage = null;
    }
  });
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-2xl max-h-[85vh] flex flex-col p-0 overflow-hidden">
    <!-- Header -->
    <div class="px-6 pt-6 pb-4 border-b border-border bg-card">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <div class="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <FileText class="size-4.5" />
          </div>
          <div>
            <Dialog.Title class="text-base font-semibold">
              Medical Chart & History
            </Dialog.Title>
            <Dialog.Description class="text-xs text-muted-foreground">
              Clinical diagnoses, prescriptions, and SOAP records for {patient?.full_name}.
            </Dialog.Description>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          class="h-8 px-2.5 text-xs cursor-pointer"
          onclick={loadHistory}
          disabled={isLoading}
        >
          <RefreshCw class="size-3.5 mr-1.5 {isLoading ? 'animate-spin' : ''}" />
          Refresh
        </Button>
      </div>

      {#if patient}
        <div class="mt-3 grid grid-cols-3 gap-2 bg-muted/40 p-2.5 rounded-lg text-xs">
          <div>
            <span class="text-muted-foreground">Patient:</span>
            <span class="font-medium text-foreground ml-1">{patient.full_name}</span>
          </div>
          <div>
            <span class="text-muted-foreground">Record ID:</span>
            <span class="font-mono font-medium text-foreground ml-1">#{patient.id}</span>
          </div>
          <div>
            <span class="text-muted-foreground">Age / Contact:</span>
            <span class="font-medium text-foreground ml-1">
              {patient.age} yrs {patient.contact ? `• ${patient.contact}` : ""}
            </span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Scrollable Content -->
    <div class="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
      {#if isLoading}
        <div class="flex flex-col items-center justify-center py-12 text-sm text-muted-foreground gap-2">
          <RefreshCw class="animate-spin size-5 text-primary" />
          <span>Retrieving signed clinical records...</span>
        </div>
      {:else if errorMessage}
        <div class="rounded-lg bg-destructive/10 border border-destructive/20 p-4 text-xs text-destructive">
          {errorMessage}
        </div>
      {:else if records.length === 0}
        <div class="flex flex-col items-center justify-center py-12 text-center text-muted-foreground gap-2">
          <FileText class="size-8 opacity-30" />
          <p class="text-sm font-medium text-foreground">No Medical Records Found</p>
          <p class="text-xs max-w-sm">
            This patient has no completed consultation notes or prescriptions on file yet.
          </p>
        </div>
      {:else}
        <div class="flex flex-col gap-4">
          {#each records as record, idx (record.id)}
            <div class="rounded-xl border border-border bg-card p-4 shadow-xs flex flex-col gap-3">
              <!-- Card Header -->
              <div class="flex items-start justify-between gap-2 border-b border-border/60 pb-2.5">
                <div>
                  <div class="flex items-center gap-2">
                    <Badge variant="secondary" class="font-semibold text-xs">
                      {record.diagnosis}
                    </Badge>
                    <span class="text-[11px] font-mono text-muted-foreground">
                      Record #{record.id}
                    </span>
                  </div>
                  <p class="text-xs text-muted-foreground mt-1 flex items-center gap-1.5">
                    <User class="size-3 text-muted-foreground" />
                    <span>Attending: <strong>{record.doctor_name}</strong></span>
                    {#if record.doctor_specialty}
                      <span class="text-muted-foreground">({record.doctor_specialty})</span>
                    {/if}
                  </p>
                </div>

                <span class="text-[11px] text-muted-foreground font-mono tabular-nums flex items-center gap-1">
                  <Calendar class="size-3 text-muted-foreground" />
                  {formatDate(record.created_at)}
                </span>
              </div>

              <!-- Symptoms & Clinical Notes -->
              {#if record.symptoms || record.clinical_notes}
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs bg-muted/20 p-2.5 rounded-lg">
                  {#if record.symptoms}
                    <div>
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Reported Symptoms
                      </p>
                      <p class="text-foreground mt-0.5 whitespace-pre-wrap">{record.symptoms}</p>
                    </div>
                  {/if}
                  {#if record.clinical_notes}
                    <div>
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Clinical Examination / Findings
                      </p>
                      <p class="text-foreground mt-0.5 whitespace-pre-wrap">{record.clinical_notes}</p>
                    </div>
                  {/if}
                </div>
              {/if}

              <!-- Prescription Box -->
              {#if record.prescription}
                <div class="rounded-lg border border-border bg-muted/40 p-2.5 text-xs text-foreground flex flex-col gap-1">
                  <div class="flex items-center gap-1.5 font-semibold text-primary text-[11px] uppercase tracking-wider">
                    <Pill class="size-3.5 text-primary" />
                    <span>Prescribed Medication (Rx)</span>
                  </div>
                  <p class="font-mono text-xs whitespace-pre-wrap pl-5">{record.prescription}</p>
                </div>
              {/if}

              <!-- Follow-up Advice -->
              {#if record.follow_up_advice}
                <div class="text-xs text-muted-foreground flex items-baseline gap-1.5 pl-1">
                  <span class="font-semibold text-foreground">Follow-up / Advice:</span>
                  <span>{record.follow_up_advice}</span>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <div class="px-6 py-3 border-t border-border bg-card flex justify-end">
      <Button
        variant="outline"
        size="sm"
        onclick={() => (open = false)}
        class="cursor-pointer"
      >
        Close Chart
      </Button>
    </div>
  </Dialog.Content>
</Dialog.Root>
