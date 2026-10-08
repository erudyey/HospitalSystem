import { appointmentsWithinDates, dateFilterError } from "./schedule.ts";
import type { Appointment } from "./api.ts";

function equal(actual: unknown, expected: unknown) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(JSON.stringify({ actual, expected }));
}
const rows = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"].map((app_date, id) => ({ id, app_date } as Appointment));

Deno.test("schedule date filters include both range boundaries and one selected day", () => {
  equal(appointmentsWithinDates(rows, { mode: "range", from: "2026-09-02", to: "2026-09-03" }).map(row => row.id), [1, 2]);
  equal(appointmentsWithinDates(rows, { mode: "day", from: "2026-09-02", to: "" }).map(row => row.id), [1]);
  equal(appointmentsWithinDates(rows, { mode: "all", from: "", to: "" }).length, 4);
});

Deno.test("invalid ranges expose an error instead of unrelated or zero-valued totals", () => {
  const reversed = { mode: "range", from: "2026-09-03", to: "2026-09-02" } as const;
  equal(dateFilterError(reversed), "The end date must be on or after the start date.");
  equal(appointmentsWithinDates(rows, reversed), []);
  equal(dateFilterError({ mode: "day", from: "2026-02-30", to: "" }), "Choose a valid start date.");
  equal(dateFilterError({ mode: "range", from: "2026-09-01", to: "" }), "Choose a valid end date.");
});
