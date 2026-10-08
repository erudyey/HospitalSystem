/** Calendar values follow the clinic clock, including its UTC offset. */
export function isCalendarDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000")) return false;
  const parsed = new Date(value + "T12:00:00Z");
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function formatClinicDate(clinicNow: string): string {
  const day = clinicNow.slice(0, 10);
  if (!isCalendarDate(day)) return "Clinic date unavailable";
  return new Intl.DateTimeFormat("en", {
    weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC",
  }).format(new Date(day + "T12:00:00Z"));
}

export function calendarDateOffset(clinicNow: string, days: number): string {
  const day = new Date(clinicNow.slice(0, 10) + "T12:00:00Z");
  day.setUTCDate(day.getUTCDate() + days);
  return day.toISOString().slice(0, 10);
}

export function nextClinicSlot(
  clinicNow: string,
): { date: string; time: string } {
  const slot = new Date(clinicNow.slice(0, 19) + "Z");
  slot.setUTCMinutes(
    slot.getUTCMinutes() + 15 - slot.getUTCMinutes() % 15,
    0,
    0,
  );
  return {
    date: slot.toISOString().slice(0, 10),
    time: slot.toISOString().slice(11, 16),
  };
}
