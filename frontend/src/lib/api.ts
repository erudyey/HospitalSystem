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

export function getUserToken(): string {
  try {
    return localStorage.getItem("user_token") || sessionStorage.getItem("user_token") || "";
  } catch {
    return "";
  }
}

export function setUserToken(token: string, remember: boolean = true): void {
  try {
    if (remember) {
      localStorage.setItem("user_token", token);
    } else {
      sessionStorage.setItem("user_token", token);
    }
  } catch {
    // Ignore storage restrictions
  }
}

export function clearUserToken(): void {
  try {
    localStorage.removeItem("user_token");
    sessionStorage.removeItem("user_token");
  } catch {
    // Ignore storage restrictions
  }
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
    request<{ status: string; version: string }>("/api/health/"),

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
    },
  ) =>
    request<Appointment>("/api/appointments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Reschedule or update an appointment */
  updateAppointment: (
    appointmentId: number,
    data: {
      doctor_name?: string;
      app_date?: string;
      app_time?: string;
      reason_for_visit?: string;
      doctor_id?: number | null;
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
    duration: number = 15,
    excludeId?: number,
  ) => {
    const params = new URLSearchParams({
      doctor_id: String(doctorId),
      date: dateStr,
      time: timeStr,
      duration: String(duration),
    });
    if (excludeId !== undefined) {
      params.set("exclude_id", String(excludeId));
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

    login: async (credentials: { username: string; password: string }) => {
      const resp = await request<UserSession>("/api/auth/login/", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
      if (resp?.token) {
        setUserToken(resp.token);
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

    updateProfile: (data: {
      full_name?: string;
      contact?: string;
      specialty?: string;
      license_number?: string;
      current_password?: string;
      new_password?: string;
    }) =>
      request<{ user: StaffUser }>("/api/auth/profile/", {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    listDoctors: () => request<StaffUser[]>("/api/doctors/"),
  },

  // Clinical & Doctor Methods
  clinical: {
    getDoctorQueue: (dateStr?: string) => {
      const q = dateStr ? `?date=${encodeURIComponent(dateStr)}` : "";
      return request<DoctorQueueResponse>(`/api/doctor/queue/${q}`);
    },

    getDoctorPatients: (query?: string) => {
      const q = query ? `?q=${encodeURIComponent(query)}` : "";
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
