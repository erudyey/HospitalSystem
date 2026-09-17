/**
 * Strongly typed API client for HospitalSystem.
 * Handles loopback session token, CSRF cookie forwarding, and request cancellation.
 */

export interface Patient {
  id: number;
  full_name: string;
  contact: string;
  age: number;
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
  const match = document.cookie.match(new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"));
  return match ? decodeURIComponent(match[3]) : null;
}

function getSessionToken(): string {
  // In desktop pywebview mode, token is injected into window.__SESSION_TOKEN__
  const win = window as unknown as { __SESSION_TOKEN__?: string };
  return win.__SESSION_TOKEN__ || "";
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

  return response.json() as Promise<T>;
}

export const api = {
  /** Initialize connection and set CSRF cookie */
  healthCheck: () => request<{ status: string; version: string }>("/api/health/"),

  /** List / search patients */
  listPatients: (query?: string) => {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    return request<Patient[]>(`/api/patients/${q}`);
  },

  /** Register a new patient */
  registerPatient: (data: { full_name: string; contact?: string; age: number }) =>
    request<Patient>("/api/patients/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** List appointments for a patient (with AbortSignal support) */
  listPatientAppointments: (patientId: number, signal?: AbortSignal) =>
    request<Appointment[]>(`/api/patients/${patientId}/appointments/`, { signal }),

  /** Book an appointment */
  bookAppointment: (data: { patient_id: number; doctor_name: string; app_date: string }) =>
    request<Appointment>("/api/appointments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Update appointment status */
  updateAppointmentStatus: (appointmentId: number, status: "Completed" | "Cancelled") =>
    request<Appointment>(`/api/appointments/${appointmentId}/status/`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
