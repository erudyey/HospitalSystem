# Demo script and runbook

This is an eight-minute presentation for three speakers. Keep one minute free for delays so the presentation stays under ten minutes. The spoken lines are prompts, not lines that must be memorized.

## Part 1: Introduction (Speaker 1, about 60 seconds)

### Prepare before presenting

- Launch the `0.1.0-beta.1` build and confirm it opens normally.
- Choose **Try demo** from the sign-in screen. The app restarts when moving between clinic and demo mode. Wait for the demo sign-in screen.
- Confirm the chooser lists **Maria Santos** and the physician you will use. Use Dr. Chloe Tan if available.
- Prepare one fictional patient: **Jordan Lee**, age 29, contact `0917 555 0142`.
- Prepare notes for the consultation: symptoms "Headache and sore throat for two days"; diagnosis "Acute upper respiratory tract infection"; notes "Stable vital signs. Mild throat redness observed."; prescription "Paracetamol 500 mg as needed for fever"; follow-up "Return in seven days if symptoms persist."
- Choose a future appointment time and a second time at least 15 minutes away. Record Jordan's generated patient ID during rehearsal.

### Say this

"Good day. We are presenting HospitalSystem, a desktop application for a small clinic. It follows a patient from the front desk to the consultation room and into their clinical record.

The receptionist workspace handles patient registration, appointment scheduling, and check-in. The physician workspace handles the waiting room, consultations, and signed medical records. We will use one fictional patient so the handoff between the two roles is easy to follow.

The application runs locally on the computer. Clinic records are stored in a local SQLite database, and demo records use a separate database. [Receptionist speaker], please start with the front-desk workflow."

Talking points: local desktop app; receptionist and physician roles; one patient will move through the full workflow.

## Part 2: Receptionist demo (Speaker 2, about 3 minutes 30 seconds)

| Time | Action | Say | Expected result |
| --- | --- | --- | --- |
| 0:00 | Choose **Maria Santos** on the demo sign-in screen. | "Demo accounts let us enter a prepared role without typing sample credentials." | The receptionist workspace opens. |
| 0:15 | Open **Patients**. Point out search, sortable columns, pagination, and appointment counts. Select **Register Patient**. | "This is the front-desk registry." | Patient list and registration action are visible. |
| 0:35 | Register Jordan Lee. Save, then search for "Jordan". | "The record is created first, so the appointment has a registered patient behind it." | Jordan appears in the filtered list. |
| 0:55 | Open Jordan's menu, choose **Edit Details**, change the contact to `0917 555 0199`, and save. | "Reception can correct contact information without changing clinical history." | Updated contact is shown. |
| 1:15 | Open **Appointments** and select **New Appointment**. Choose Jordan and Dr. Chloe Tan. Set the prepared future date and first time. Add "Routine follow-up" and book it. | "Scheduling uses registered physicians and checks active appointments around the selected time." | A scheduled appointment appears. |
| 1:45 | Create another appointment for the same doctor within 15 minutes. Let the warning appear. Change it to the prepared available time, then book. | "The warning appears before submission, and the server checks the same rule when it saves." | Warning clears after the time changes. |
| 2:15 | Cancel the first scheduled appointment, then choose **Reopen as Scheduled**. | "Cancelled appointments stay in the record and can be restored after validation." | Status changes to Cancelled, then Scheduled. |
| 2:40 | Create another appointment for Jordan and Dr. Chloe Tan. Enter a short reason and choose **Walk-in / Check in now**. | "A walk-in uses the clinic's current date and time, then enters the waiting room." | Jordan has a Checked In appointment. |
| 3:05 | Filter to **Waiting Room**. | "Jordan Lee is checked in for Dr. Chloe Tan." | Jordan is visible in the waiting-room filter. |

Optional cue: filters, search, sorting, and pagination help reception find an active visit.

Handoff: "Jordan Lee is checked in with Dr. Chloe Tan. [Doctor speaker] will continue the visit."

## Part 3: Doctor demo and closing (Speaker 3, about 3 minutes 30 seconds)

| Time | Action | Say | Expected result |
| --- | --- | --- | --- |
| 0:00 | Sign out. Choose **Dr. Chloe Tan** from the demo account chooser. | "The doctor sees a workspace for their own queue and patients." | Doctor workspace opens. |
| 0:20 | Open **Waiting Room**, **Today's Schedule**, and **My Patients**. Return to Waiting Room. | "The doctor has a queue, today's schedule, and a patient roster." | The three tabs and counts are visible. |
| 0:40 | Find Jordan and begin the consultation. | "Starting the consultation changes the visit from checked in to in consultation." | Jordan enters the active consultation state. |
| 1:00 | Open the consultation form. Expand prior history if available. Enter the prepared symptoms, diagnosis, notes, prescription, and follow-up advice. | "The physician records the consultation here, with prior history available for context." | Required fields contain the prepared details. |
| 1:45 | Choose **Complete Consultation & Sign Record**. | "Signing completes the appointment and creates the clinical record." | Jordan's appointment is Completed. |
| 2:05 | Open Jordan's patient chart. | "The chart keeps the completed visit with the patient's medical history." | Jordan's signed record is visible. |
| 2:25 | Open **Settings** and point to Staff Profile fields. Do not save changes. | "Staff can maintain their own profile. Credential changes ask for the current password." | Profile fields are visible. |
| 2:45 | Sign out, return to Maria Santos, and show Jordan's completed appointment or patient record. | "The completed record protects the patient's clinical history from ordinary deletion." | Completed status and protected-history behavior are visible. |
| 3:10 | Sign out and close the app. | "That completes the patient journey from registration to a signed clinical record." | The sign-in screen remains visible after logout. |

### Recovery notes

- If a demo account is unavailable, return to clinic mode, choose **Try demo** again, and wait for the chooser.
- If a conflict warning remains, choose a time at least 15 minutes away from the conflicting active appointment. Do not use an override in this short presentation.
- If Jordan is missing from Waiting Room, confirm the walk-in was assigned to Dr. Chloe Tan. Create a new walk-in if needed.
- If a transition takes too long, wait for the sign-in screen after the restart. If it does not return, relaunch the app and choose the demo account again.

### Rehearsal checklist

- Time the full route. It should take eight minutes and leave one minute before the ten-minute limit.
- Confirm visible labels against the current build before presenting.
- Use disposable demo data for rehearsal. Demo changes persist until reset.
- Keep screenshots of the doctor queue and completed patient chart in case a live transition fails.
