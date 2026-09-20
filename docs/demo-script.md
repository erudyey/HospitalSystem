# Demo instructions

## Before you start

- Open the `0.1.0-beta.1` build, choose **Try demo**, and wait for the app to restart.
- Check that **Maria Santos** and **Dr. Chloe Tan** appear in the demo account chooser.
- Use a fictional patient: **Jordan Lee**, age **29**, contact **0917 555 0142**.
- Pick a future date and two available appointment times at least 15 minutes apart.
- Keep these sample consultation details ready:
  - Symptoms: Headache and sore throat for two days.
  - Diagnosis: Acute upper respiratory tract infection.
  - Notes: Stable vital signs. Mild throat redness observed.
  - Prescription: Paracetamol 500 mg as needed for fever.
  - Follow-up: Return in seven days if symptoms persist.

## Speaker 1: Introduce the app

Briefly explain that HospitalSystem is a local desktop app for a small clinic.
Receptionists register patients, book appointments, and check them in. Doctors
handle consultations and sign medical records. Clinic and demo data use separate
local databases.

Introduce Jordan as the patient you will follow through the demo, then hand over
to the receptionist speaker.

## Speaker 2: Show the receptionist workflow

1. Sign in as **Maria Santos**. Open **Patients** and point out search, sorting,
   pagination, and appointment counts.
2. Select **Register Patient**, enter Jordan's details, and save. Search for
   Jordan and note the generated patient ID.
3. Open **Edit Details**, change the contact to **0917 555 0199**, and save.
4. Open **Appointments** and select **New Appointment**. Choose Jordan and
   **Dr. Chloe Tan**, use your prepared date and first time, and enter
   **Routine follow-up** as the reason. Book the appointment.
5. Try another booking for the same doctor within 15 minutes of the first.
   Show the conflict warning, switch to your second available time, and book it.
6. Cancel the first appointment, then select **Reopen as Scheduled** to show
   that a cancelled booking can be restored after validation.
7. Create a walk-in for Jordan with Dr. Chloe Tan. Enter a reason and choose
   **Walk-in / Check in now**. This uses the current date and time.
8. Filter to **Waiting Room**, show Jordan's checked-in visit, and hand over
   to the doctor speaker.

## Speaker 3: Show the consultation

1. Sign out and choose **Dr. Chloe Tan** from the demo account chooser.
2. Briefly show **Waiting Room**, **Today's Schedule**, and **My Patients**.
   Return to **Waiting Room** and start Jordan's consultation.
3. Open the consultation form, show prior history if available, and enter the
   prepared consultation details.
4. Select **Complete Consultation & Sign Record**. Open Jordan's patient chart
   and show the signed record and completed visit.
5. Open **Settings** and point out the staff profile fields without saving
   changes. Mention that credential changes require the current password.
6. Sign out, return to **Maria Santos**, and show Jordan's completed appointment.
   Explain that completed visits and patients with clinical history are
   protected from deletion.
7. Sign out and show that the app stays on the sign-in screen. Recap Jordan's
   registration, check-in, consultation, and signed record, then close the app.

## If something goes wrong

- **Missing demo account:** Return to clinic mode and choose **Try demo** again.
- **Schedule conflict:** Choose a time at least 15 minutes from the conflicting
  appointment. Skip overrides for this demo.
- **Jordan missing from the queue:** Check that the walk-in belongs to
  Dr. Chloe Tan. Create another walk-in if needed.
- **Restart stalls:** Relaunch the app and select the demo account again.

Rehearse with disposable demo data; changes persist until reset. Check the button
labels against the build and keep screenshots of the doctor queue and completed
chart as a backup.
