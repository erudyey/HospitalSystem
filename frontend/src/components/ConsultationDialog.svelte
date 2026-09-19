<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import {
    api,
    type Appointment,
    type StaffUser,
    type MedicalRecord,
    type ApiError,
  } from "$lib/api";
  import { toast } from "$lib/toast.svelte";
  import {
    Stethoscope,
    CheckCircle2,
    FileText,
    Pill,
    AlertCircle,
    ChevronDown,
    ChevronUp,
    Clock,
    User,
    Loader2,
  } from "lucide-svelte";

  interface Props {
    open?: boolean;
    appointment?: Appointment | null;
    activeDoctor?: StaffUser | null;
    onComplete?: () => void;
  }

  let {
    open = $bindable(false),
    appointment = null,
    activeDoctor = null,
    onComplete,
  }: Props = $props();

  let diagnosis = $state("");
  let symptoms = $state("");
  let clinicalNotes = $state("");
  let prescription = $state("");
  let followUpAdvice = $state("");

  let isSubmitting = $state(false);
  let formErrors = $state<Record<string, string[]>>({});

  let pastRecords = $state<MedicalRecord[]>([]);
  let isLoadingHistory = $state(false);
  let isHistoryExpanded = $state(false);

  function resetForm() {
    diagnosis = "";
    symptoms = appointment?.reason_for_visit || "";
    clinicalNotes = "";
    prescription = "";
    followUpAdvice = "";
    formErrors = {};
    isHistoryExpanded = false;
  }

  async function loadPatientHistory(patientId: number) {
    isLoadingHistory = true;
    try {
      pastRecords = await api.clinical.getPatientMedicalHistory(patientId);
    } catch {
      pastRecords = [];
    } finally {
      isLoadingHistory = false;
    }
  }

  $effect(() => {
    if (open && appointment) {
      resetForm();
      loadPatientHistory(appointment.patient_id);
    }
  });

  async function handleCompleteConsultation(e: SubmitEvent) {
    e.preventDefault();
    if (!appointment || !activeDoctor) return;

    formErrors = {};
    const trimmedDiagnosis = diagnosis.trim();
    if (!trimmedDiagnosis) {
      formErrors = { diagnosis: ["Primary clinical diagnosis is required."] };
      return;
    }

    isSubmitting = true;
    try {
      await api.clinical.createMedicalRecord({
        patient_id: appointment.patient_id,
        doctor_id: activeDoctor.id,
        appointment_id: appointment.id,
        diagnosis: trimmedDiagnosis,
        symptoms: symptoms.trim(),
        clinical_notes: clinicalNotes.trim(),
        prescription: prescription.trim(),
        follow_up_advice: followUpAdvice.trim(),
      });

      toast.success(
        `Consultation completed for ${appointment.patient_name}. Medical record saved.`
      );
      open = false;
      onComplete?.();
    } catch (err) {
      const e = err as ApiError;
      formErrors = e.fields || { general: [e.message] };
    } finally {
      isSubmitting = false;
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-3xl max-h-[90vh] flex flex-col p-0 overflow-hidden">
    <!-- Header: Patient Details & Triage Info -->
    <div class="px-6 pt-5 pb-4 border-b border-border bg-card">
      <div class="flex items-start justify-between">
        <div class="flex items-center gap-2.5">
          <div class="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Stethoscope class="size-5" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <Dialog.Title class="text-base font-semibold">
                Clinical Consultation (SOAP)
              </Dialog.Title>
              <Badge variant="default" class="text-[11px] font-medium">
                In Consultation
              </Badge>
            </div>
            <Dialog.Description class="text-xs text-muted-foreground mt-0.5">
              Attending: Dr. {activeDoctor?.full_name?.replace(/^Dr\.\s*/i, "") || "Physician"}
              {activeDoctor?.specialty ? `(${activeDoctor.specialty})` : ""}
            </Dialog.Description>
          </div>
        </div>

        <div class="text-right text-xs">
          <span class="font-mono text-muted-foreground">Appt #{appointment?.id}</span>
          <p class="text-[11px] text-muted-foreground tabular-nums">
            {appointment?.app_date} {appointment?.app_time ? `• ${appointment.app_time}` : ""}
          </p>
        </div>
      </div>

      <!-- Patient Demographics Banner -->
      {#if appointment}
        <div class="mt-3 grid grid-cols-3 gap-2 bg-muted/30 border border-border/60 p-2.5 rounded-lg text-xs">
          <div>
            <span class="text-muted-foreground">Patient:</span>
            <span class="font-semibold text-foreground ml-1">{appointment.patient_name}</span>
            <span class="text-muted-foreground font-mono ml-1">#{appointment.patient_id}</span>
          </div>
          <div class="col-span-2">
            <span class="text-muted-foreground">Chief Complaint / Triage:</span>
            <span class="font-medium text-foreground ml-1 italic">
              {appointment.reason_for_visit || "General checkup / No chief complaint specified"}
            </span>
          </div>
        </div>
      {/if}

      <!-- Collapsible Past History Toggle -->
      <div class="mt-2.5 flex items-center justify-between">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline cursor-pointer"
          onclick={() => (isHistoryExpanded = !isHistoryExpanded)}
        >
          <FileText class="size-3.5" />
          <span>Prior Medical History ({pastRecords.length} record{pastRecords.length === 1 ? "" : "s"})</span>
          {#if isHistoryExpanded}
            <ChevronUp class="size-3.5" />
          {:else}
            <ChevronDown class="size-3.5" />
          {/if}
        </button>
      </div>

      <!-- Collapsible Medical History Drawer -->
      {#if isHistoryExpanded}
        <div class="mt-2 max-h-36 overflow-y-auto rounded-lg border border-border bg-muted/20 p-2.5 flex flex-col gap-2 text-xs">
          {#if isLoadingHistory}
            <div class="flex items-center gap-2 text-muted-foreground py-2 justify-center">
              <Loader2 class="size-3.5 animate-spin" />
              <span>Loading patient history...</span>
            </div>
          {:else if pastRecords.length === 0}
            <p class="text-muted-foreground italic text-center py-2">
              No previous clinical notes on record for this patient.
            </p>
          {:else}
            {#each pastRecords as rec (rec.id)}
              <div class="rounded border border-border/80 bg-background p-2 text-xs flex flex-col gap-1">
                <div class="flex items-center justify-between font-semibold">
                  <span class="text-foreground">{rec.diagnosis}</span>
                  <span class="text-[10px] font-mono text-muted-foreground">{rec.created_at?.slice(0, 10)}</span>
                </div>
                {#if rec.prescription}
                  <p class="text-primary text-[11px] font-mono">Rx: {rec.prescription}</p>
                {/if}
                <p class="text-[11px] text-muted-foreground">Dr. {rec.doctor_name}</p>
              </div>
            {/each}
          {/if}
        </div>
      {/if}
    </div>

    <!-- Scrollable SOAP Form -->
    <form onsubmit={handleCompleteConsultation} class="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
      <!-- 1. Symptoms (Subjective) -->
      <div>
        <label for="soapSymptoms" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          Subjective -- Symptoms & Chief Complaints
        </label>
        <textarea
          id="soapSymptoms"
          rows={2}
          placeholder="Patient reports onset of headache, sore throat for 3 days, low-grade fever..."
          class="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-xs focus:outline-none focus:ring-1 focus:ring-ring resize-y"
          bind:value={symptoms}
          disabled={isSubmitting}
        ></textarea>
      </div>

      <!-- 2. Diagnosis (Assessment - Required) -->
      <div>
        <label for="soapDiagnosis" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          Assessment -- Primary Diagnosis <span class="text-destructive">*</span>
        </label>
        <Input
          id="soapDiagnosis"
          type="text"
          placeholder="e.g. Acute Upper Respiratory Tract Infection (URTI), Essential Hypertension..."
          bind:value={diagnosis}
          aria-invalid={!!formErrors.diagnosis}
          disabled={isSubmitting}
          class="h-9 font-medium"
        />
        {#if formErrors.diagnosis}
          <p class="text-xs text-destructive mt-1">{formErrors.diagnosis.join(" ")}</p>
        {/if}
      </div>

      <!-- 3. Clinical Notes (Objective / Examination) -->
      <div>
        <label for="soapNotes" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          Objective -- Physical Examination & Clinical Findings
        </label>
        <textarea
          id="soapNotes"
          rows={3}
          placeholder="BP: 120/80 mmHg, HR: 78 bpm, Temp: 37.4C. Pharyngeal erythema present, clear breath sounds bilaterally..."
          class="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-xs focus:outline-none focus:ring-1 focus:ring-ring resize-y"
          bind:value={clinicalNotes}
          disabled={isSubmitting}
        ></textarea>
      </div>

      <!-- 4. Prescription (Plan - Rx) -->
      <div>
        <label for="soapRx" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1 flex items-center gap-1.5">
          <Pill class="size-3.5 text-sky-600" />
          <span>Plan -- Prescription & Medication Orders (Rx)</span>
        </label>
        <textarea
          id="soapRx"
          rows={3}
          placeholder="Amoxicillin 500mg capsules, 1 cap TID for 7 days&#10;Paracetamol 500mg tablets, 1 tab Q6H PRN fever&#10;Oral rehydration salts 1 sachet in 1L water..."
          class="w-full rounded-md border border-input bg-background px-3 py-2 text-xs font-mono shadow-xs focus:outline-none focus:ring-1 focus:ring-ring resize-y"
          bind:value={prescription}
          disabled={isSubmitting}
        ></textarea>
      </div>

      <!-- 5. Follow-up Advice (Disposition) -->
      <div>
        <label for="soapFollowUp" class="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          Disposition -- Patient Advice & Follow-up Instructions
        </label>
        <Input
          id="soapFollowUp"
          type="text"
          placeholder="e.g. Return in 7 days for review. Rest and maintain fluid intake. Return sooner if fever exceeds 39C."
          bind:value={followUpAdvice}
          disabled={isSubmitting}
          class="h-9"
        />
      </div>

      {#if formErrors.general}
        <div class="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive flex items-center gap-2">
          <AlertCircle class="size-4 shrink-0" />
          <span>{formErrors.general.join(" ")}</span>
        </div>
      {/if}

      <div class="pt-2"></div>
    </form>

    <!-- Footer: Complete Action -->
    <div class="px-6 py-3 border-t border-border bg-card flex items-center justify-between">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onclick={() => (open = false)}
        disabled={isSubmitting}
        class="text-xs cursor-pointer"
      >
        Exit (Keep In Consultation)
      </Button>

      <Button
        type="submit"
        onclick={handleCompleteConsultation}
        disabled={isSubmitting || !diagnosis.trim()}
        class="cursor-pointer font-medium"
      >
        {#if isSubmitting}
          <Loader2 class="size-4 animate-spin mr-1.5" />
        {:else}
          <CheckCircle2 class="size-4 mr-1.5" />
        {/if}
        Complete Consultation & Sign Record
      </Button>
    </div>
  </Dialog.Content>
</Dialog.Root>
