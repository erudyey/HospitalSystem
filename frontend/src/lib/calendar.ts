/** Calendar values follow the clinic clock, including its UTC offset. */
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
