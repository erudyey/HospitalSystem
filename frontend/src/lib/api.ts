/**
 * Strongly typed API client for HospitalSystem.
 * Handles loopback session token, CSRF cookie forwarding, and request cancellation.
 */

export interface Patient {
  id: number;
  full_name: string;
  contact: string;
  age: number;
  appointment_count?: number;
  active_appointment_count?: number;
}

export interface Appointment {
  id: number;
  patient_id: number;
  patient_name: string;
  doctor_name: string;
  app_date: string;
  status: "Scheduled" | "Completed" | "Cancelled";
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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});

  // Set JSON headers
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Set desktop loopback session token
  const token = getSessionToken();
  if (token) {
    headers.set("X-Session-Token", token);
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

  /** Delete a patient and cascade delete associated appointments */
  deletePatient: (patientId: number) =>
    request<void>(`/api/patients/${patientId}/`, {
      method: "DELETE",
    }),

  /** List all appointments */
  listAllAppointments: () => request<Appointment[]>("/api/appointments/"),

  /** Get single appointment detail */
  getAppointment: (appointmentId: number) =>
    request<Appointment>(`/api/appointments/${appointmentId}/`),

  /** Book an appointment */
  bookAppointment: (
    data: { patient_id: number; doctor_name: string; app_date: string },
  ) =>
    request<Appointment>("/api/appointments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Reschedule or update an appointment */
  updateAppointment: (
    appointmentId: number,
    data: { doctor_name: string; app_date: string },
  ) =>
    request<Appointment>(`/api/appointments/${appointmentId}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /** Delete an appointment */
  deleteAppointment: (appointmentId: number) =>
    request<void>(`/api/appointments/${appointmentId}/`, {
      method: "DELETE",
    }),

  /** Update appointment status */
  updateAppointmentStatus: (
    appointmentId: number,
    status: "Scheduled" | "Completed" | "Cancelled",
  ) =>
    request<Appointment>(`/api/appointments/${appointmentId}/status/`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
