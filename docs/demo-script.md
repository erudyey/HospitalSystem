# Demo script

A walkthrough for presenting HospitalSystem to an audience. Three parts. The first part is prose you can read aloud or paraphrase; the other two are bullet-point talking points you can riff on.

---

## Part 1: Introduction (read aloud or paraphrase)

HospitalSystem is a desktop clinic management app that runs as a single executable, no server setup, no database configuration, no internet connection required. You double-click it and it is ready.

The system is built around two roles. A receptionist handles the front desk: registering patients, booking appointments, and checking people in. A doctor handles the clinical side: seeing the waiting room queue, conducting consultations, and writing up SOAP notes. Each role gets its own workspace, and the data flows between them in real time.

The whole thing is packaged as a native desktop window. On Windows it uses WebView2; on macOS it uses WebKit. The backend is a Django REST API running locally on a loopback port, so everything stays on the machine. There is no cloud, no external service, and nothing listening on a public network interface.

---

## Part 2: Receptionist walkthrough (talking points)

**Logging in**

- App starts logged out by default. Show the sign-in screen.
- Log in as the receptionist. Point out the "Keep me signed in" checkbox -- token goes to `localStorage` if checked, `sessionStorage` if not. Restart the app to show session restoration.

**Patient registry**

- Open the Patients tab. Show the list with appointment counts per row.
- Register a new patient: name, contact number, age.
- Search by name, ID, or phone. Filter clears with Escape.
- Try to delete a patient with completed records. Show the error -- deletion is blocked to protect the audit trail.

**Booking an appointment**

- Open the Appointments tab. Show the filter bar: All, Waiting Room, Scheduled, Consulting, Completed, Cancelled.
- Click "New Appointment". Pick the patient, pick a doctor from the dropdown (populated from staff), set a date and time, enter a reason.
- Book a second appointment for the same doctor within 15 minutes of the first. Show the conflict warning banner. Adjust the time to resolve it.
- Use "Book & Check In" to immediately move the patient to the waiting room in one step.

**Managing the queue**

- Show the Waiting Room filter. The patient just checked in is there.
- Demonstrate changing status: Check In -> In Consultation -> Completed.
- Show that completed appointments are locked -- the edit and delete controls are gone.

---

## Part 3: Doctor walkthrough (talking points)

**Switching roles**

- Log out. Log in as a doctor. The workspace changes completely.
- Point out the three tabs: Waiting Room, Today's Schedule, My Patients.

**Waiting room and consultation**

- The checked-in patient from the receptionist demo appears in the Waiting Room tab with a live count badge.
- Start the consultation. Status moves to In Consultation on both the doctor and receptionist sides simultaneously.

**SOAP notes**

- Open the consultation dialog. Fill in the fields: diagnosis, subjective symptoms, clinical notes, prescription, follow-up date.
- Submit. The appointment moves to Completed. The record is now immutable.
- Open the patient chart. Show the full medical history in date order. Point out that only the authoring doctor can edit their own notes.

**My Patients**

- Switch to the My Patients tab. The patient from the consultation now appears in the roster.
- The patient cannot be deleted from the registry because they have a completed record. Show this if not already demonstrated.

**Settings**

- Open Settings while logged in as the doctor. Show the Staff Profile tab: edit name, specialty, license number, change password.
- Log out and open Settings again. The Profile tab is hidden. Only System Settings is visible -- demo mode toggle and database health status.
- Toggle demo mode on to show seed data. Toggle it off. Point out that toggling demo mode never logs anyone out.
