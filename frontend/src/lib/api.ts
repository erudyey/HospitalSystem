/**
 * Strongly typed API client for HospitalSystem.
 * Handles loopback session token, user bearer authentication, CSRF cookie forwarding,
 * and standard error parsing.
 */

export type StaffRole = "receptionist" | "doctor";

export interface StaffUser {
  id: number;
  username: string;
  full_name: string;
  role: StaffRole;
  role_label: string;
  specialty: string;
  license_number: string;
  contact: string;
  created_at: string;
}

export interface UserSession {
  token: string;
  user: StaffUser;
}

export interface Patient {
  id: number;
  full_name: string;
  contact: string;
  age: number;
  appointment_count?: number;
  active_appointment_count?: number;
}

export type AppointmentStatus =
  | "Scheduled"
  | "Checked In"
  | "In Consultation"
  | "Completed"
  | "Cancelled";

export interface Appointment {
  id: number;
  patient_id: number;
  patient_name: string;
  doctor_id?: number | null;
  doctor_name: string;
  app_date: string;
  app_time?: string;
  reason_for_visit?: string;
  status: AppointmentStatus;
  checked_in_at?: string | null;
  conflict_override_reason?: string;
}

export interface MedicalRecord {
  id: number;
  patient_id: number;
  patient_name: string;
  doctor_id: number;
  doctor_name: string;
  doctor_specialty: string;
  appointment_id?: number | null;
  diagnosis: string;
  symptoms: string;
  clinical_notes: string;
  prescription: string;
  follow_up_advice: string;
  created_at: string;
  updated_at: string;
  revision: number;
}

export interface ConflictCheckResponse {
  has_conflict: boolean;
  conflicts: Appointment[];
}

export interface DoctorQueueResponse {
  queue: {
    checked_in: Appointment[];
    in_consultation: Appointment[];
    scheduled: Appointment[];
    completed: Appointment[];
  };
}

export interface ApiError {
  code: string;
  message: string;
  fields: Record<string, string[]>;
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(
    new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"),
  );
  return match ? decodeURIComponent(match[3]) : null;
}

function getSessionToken(): string {
  // 1. Injected directly into window memory
  const win = window as unknown as { __SESSION_TOKEN__?: string };
  if (win.__SESSION_TOKEN__) {
    try {
      sessionStorage.setItem("session_token", win.__SESSION_TOKEN__);
    } catch {
      // Ignore storage restrictions
    }
    return win.__SESSION_TOKEN__;
  }

  // 2. Cookie fallback
  const cookieToken = getCookie("session_token");
  if (cookieToken) {
    try {
      sessionStorage.setItem("session_token", cookieToken);
    } catch {
      // Ignore storage restrictions
    }
    return cookieToken;
  }

  // 3. URL search parameter fallback
  try {
    const urlToken = new URLSearchParams(window.location.search).get("token");
    if (urlToken) {
      sessionStorage.setItem("session_token", urlToken);
      return urlToken;
    }
  } catch {
    // Ignore URL parse failures
  }

  // 4. Session storage fallback
  try {
    return sessionStorage.getItem("session_token") || "";
  } catch {
    return "";
  }
}

let userToken = "";
const nativeHost = () => (window as unknown as {
  pywebview?: { api?: {
    load_remembered_token?: () => Promise<string>;
    save_remembered_token?: (token: string) => Promise<boolean>;
    clear_remembered_token?: () => Promise<void>;
  } };
}).pywebview?.api;

export function getUserToken(): string { return userToken; }

export async function restoreRememberedToken(): Promise<string> {
  try {
    const token = await nativeHost()?.load_remembered_token?.();
    userToken = token || "";
    return userToken;
  } catch { return ""; }
}

export async function setUserToken(token: string, remember: boolean = false): Promise<boolean> {
  userToken = token;
  if (!remember) return true;
  try { return await nativeHost()?.save_remembered_token?.(token) === true; } catch { return false; }
}

export function clearUserToken(): void {
  userToken = "";
  try { void nativeHost()?.clear_remembered_token?.(); } catch { /* native storage unavailable */ }
}

export async function switchApplicationMode(
  mode: "clinic" | "demo",
): Promise<void> {
  const host = (window as unknown as {
    pywebview?: { api?: { switch_mode: (mode: string) => Promise<void> } };
  }).pywebview?.api;
  if (!host?.switch_mode) {
    throw new Error(
      "Open the desktop app to switch between clinic and demo mode.",
    );
  }
  clearUserToken();
  await host.switch_mode(mode);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});

  // Set JSON headers
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Set desktop loopback session token
  const loopbackToken = getSessionToken();
  if (loopbackToken) {
    headers.set("X-Session-Token", loopbackToken);
  }

  // Set user staff token if authenticated
  const userToken = getUserToken();
  if (userToken) {
    headers.set("X-User-Token", userToken);
    headers.set("Authorization", `Bearer ${userToken}`);
  }

  // Set CSRF token for mutating methods
  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) {
    let errorData: { error?: ApiError } = {};
    try {
      errorData = await response.json();
    } catch {
      // Non-JSON response
    }
    const apiError: ApiError = errorData.error || {
      code: `HTTP_${response.status}`,
      message: response.statusText || "An unexpected error occurred.",
      fields: {},
    };
    throw apiError;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  /** Initialize connection and set CSRF cookie */
  healthCheck: () =>
    request<{ status: string; version: string; mode: "clinic" | "demo" }>(
      "/api/health/",
    ),

  /** List / search patients */
  listPatients: (query?: string) => {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    return request<Patient[]>(`/api/patients/${q}`);
  },

  /** Get single patient detail */
  getPatient: (patientId: number) =>
    request<Patient>(`/api/patients/${patientId}/`),

  /** Register a new patient */
  registerPatient: (
    data: { full_name: string; contact?: string; age: number },
  ) =>
    request<Patient>("/api/patients/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Update an existing patient */
  updatePatient: (
    patientId: number,
    data: { full_name: string; contact?: string; age: number },
  ) =>
    request<Patient>(`/api/patients/${patientId}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /** Delete a patient (guarded if completed clinical history exists) */
  deletePatient: (patientId: number) =>
    request<void>(`/api/patients/${patientId}/`, {
      method: "DELETE",
    }),

  /** List all appointments for a patient */
  listPatientAppointments: (patientId: number) =>
    request<Appointment[]>(`/api/patients/${patientId}/appointments/`),

  /** List all appointments */
  listAllAppointments: () => request<Appointment[]>("/api/appointments/"),

  /** Get single appointment detail */
  getAppointment: (appointmentId: number) =>
    request<Appointment>(`/api/appointments/${appointmentId}/`),

  /** Book an appointment with date, time, and doctor assignment */
  bookAppointment: (
    data: {
      patient_id: number;
      doctor_name: string;
      app_date: string;
      app_time?: string;
      reason_for_visit?: string;
      doctor_id?: number | null;
      initial_status?: AppointmentStatus;
      allow_conflict?: boolean;
      override_reason?: string;
    },
  ) =>
    request<Appointment>("/api/appointments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  walkIn: (data: { patient_id: number; doctor_id: number; reason_for_visit?: string; allow_conflict?: boolean; override_reason?: string }) =>
    request<Appointment>("/api/appointments/walk-in/", { method: "POST", body: JSON.stringify(data) }),

  /** Reschedule or update an appointment */
  updateAppointment: (
    appointmentId: number,
    data: {
      doctor_name?: string;
      app_date?: string;
      app_time?: string;
      reason_for_visit?: string;
      doctor_id?: number | null;
      allow_conflict?: boolean;
      override_reason?: string;
    },
  ) =>
    request<Appointment>(`/api/appointments/${appointmentId}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /** Delete an appointment (prohibited if Completed) */
  deleteAppointment: (appointmentId: number) =>
    request<void>(`/api/appointments/${appointmentId}/`, {
      method: "DELETE",
    }),

  /** Update appointment status */
  updateAppointmentStatus: (
    appointmentId: number,
    status: AppointmentStatus,
  ) =>
    request<Appointment>(`/api/appointments/${appointmentId}/status/`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  /** Check for scheduling conflicts on doctor calendar */
  checkScheduleConflict: (
    doctorId: number,
    dateStr: string,
    timeStr: string = "09:00",
    durationOrExcludeId: number = 15,
    excludeId?: number,
  ) => {
    let duration = 15;
    let exclude = excludeId;
    if (excludeId === undefined && durationOrExcludeId !== 15) {
      exclude = durationOrExcludeId;
      duration = 15;
    } else {
      duration = durationOrExcludeId;
    }

    const params = new URLSearchParams({
      doctor_id: String(doctorId),
      date: dateStr,
      time: timeStr || "09:00",
      duration: String(duration),
    });
    if (exclude !== undefined) {
      params.set("exclude_id", String(exclude));
    }
    return request<ConflictCheckResponse>(
      `/api/appointments/conflict-check/?${params.toString()}`,
    );
  },

  // Authentication & Staff Methods
  auth: {
    register: (data: {
      username: string;
      password: string;
      password_confirmation: string;
      full_name: string;
      role?: StaffRole;
      specialty?: string;
      license_number?: string;
      contact?: string;
    }) =>
      request<StaffUser>("/api/auth/register/", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    login: async (
      usernameOrCredentials: string | { username: string; password: string },
      passwordOrRemember?: string | boolean,
      remember: boolean = false,
    ) => {
      let payload: { username: string; password: string };
      let shouldRemember = remember;

      if (typeof usernameOrCredentials === "string") {
        payload = {
          username: usernameOrCredentials,
          password: typeof passwordOrRemember === "string"
            ? passwordOrRemember
            : "",
        };
      } else {
        payload = usernameOrCredentials;
        if (typeof passwordOrRemember === "boolean") {
          shouldRemember = passwordOrRemember;
        }
      }

      const resp = await request<UserSession>("/api/auth/login/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (resp?.token) {
        await setUserToken(resp.token, shouldRemember);
      }
      return resp;
    },

    me: () => request<{ user: StaffUser }>("/api/auth/me/"),

    logout: async () => {
      try {
        await request<{ status: string }>("/api/auth/logout/", {
          method: "POST",
        });
      } finally {
        clearUserToken();
      }
    },

    status: () => request<{ initial_setup_required: boolean }>("/api/auth/status/"),

    updateProfile: async (data: {
      username?: string;
      full_name?: string;
      contact?: string;
      specialty?: string;
      license_number?: string;
      current_password?: string;
      new_password?: string;
    }): Promise<StaffUser> => {
      const res = await request<{ user: StaffUser; token?: string }>("/api/auth/profile/", {
        method: "PUT",
        body: JSON.stringify(data),
      });
      if (res.token) await setUserToken(res.token, false);
      return res.user;
    },

    listDoctors: () => request<StaffUser[]>("/api/doctors/"),
  },

  // Clinical & Doctor Methods
  clinical: {
    checkScheduleConflict: (
      doctorId: number,
      dateStr: string,
      timeStr: string = "09:00",
      durationOrExcludeId: number = 15,
      excludeId?: number,
    ) => {
      let duration = 15;
      let exclude = excludeId;
      if (excludeId === undefined && durationOrExcludeId !== 15) {
        exclude = durationOrExcludeId;
        duration = 15;
      } else {
        duration = durationOrExcludeId;
      }

      const params = new URLSearchParams({
        doctor_id: String(doctorId),
        date: dateStr,
        time: timeStr || "09:00",
        duration: String(duration),
      });
      if (exclude !== undefined) {
        params.set("exclude_id", String(exclude));
      }
      return request<ConflictCheckResponse>(
        `/api/appointments/conflict-check/?${params.toString()}`,
      );
    },

    getDoctorQueue: (doctorIdOrDate?: number | string, dateStr?: string) => {
      const date = typeof doctorIdOrDate === "string"
        ? doctorIdOrDate
        : dateStr;
      const q = date ? `?date=${encodeURIComponent(date)}` : "";
      return request<DoctorQueueResponse>(`/api/doctor/queue/${q}`);
    },

    getDoctorPatients: (
      doctorIdOrQuery?: number | string,
      queryStr?: string,
    ) => {
      const qVal = typeof doctorIdOrQuery === "string"
        ? doctorIdOrQuery
        : queryStr;
      const q = qVal ? `?q=${encodeURIComponent(qVal)}` : "";
      return request<Patient[]>(`/api/doctor/patients/${q}`);
    },

    getDoctorAppointments: () =>
      request<Appointment[]>("/api/doctor/appointments/"),

    createMedicalRecord: (data: {
      patient_id: number;
      diagnosis: string;
      symptoms?: string;
      clinical_notes?: string;
      prescription?: string;
      follow_up_advice?: string;
      appointment_id?: number | null;
    }) =>
      request<MedicalRecord>("/api/medical-records/", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    updateMedicalRecord: (
      recordId: number,
      data: {
        diagnosis?: string;
        symptoms?: string;
        clinical_notes?: string;
        prescription?: string;
        follow_up_advice?: string;
        correction_reason: string;
        expected_revision?: number;
      },
    ) =>
      request<MedicalRecord>(`/api/medical-records/${recordId}/`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    getPatientMedicalHistory: (patientId: number) =>
      request<MedicalRecord[]>(`/api/patients/${patientId}/medical-records/`),
  },
};
