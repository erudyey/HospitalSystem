import type { Appointment } from "./api.ts";
import { isCalendarDate } from "./calendar.ts";

export interface DateFilter {
  mode: "all" | "day" | "range";
  from: string;
  to: string;
}

export function dateFilterError(filter: DateFilter): string | null {
  if (filter.mode === "all") return null;
  if (!isCalendarDate(filter.from)) return "Choose a valid start date.";
  if (filter.mode === "day") return null;
  if (!isCalendarDate(filter.to)) return "Choose a valid end date.";
  if (filter.to < filter.from) return "The end date must be on or after the start date.";
  return null;
}

export function appointmentsWithinDates(rows: Appointment[], filter: DateFilter): Appointment[] {
  if (dateFilterError(filter)) return [];
  if (filter.mode === "all") return rows;
  const end = filter.mode === "day" ? filter.from : filter.to;
  return rows.filter(row => row.app_date >= filter.from && row.app_date <= end);
}
