import { calendarDateOffset, nextClinicSlot } from "./calendar.ts";

function equal(actual: unknown, expected: unknown) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(JSON.stringify({ actual, expected }));
  }
}

Deno.test("clinic dates retain the clinic day rather than converting to UTC", () => {
  equal(calendarDateOffset("2026-10-08T01:05:00+08:00", 0), "2026-10-08");
  equal(calendarDateOffset("2026-12-31T23:50:00-07:00", 1), "2027-01-01");
});

Deno.test("next slot advances across midnight and exact quarter-hour boundaries", () => {
  equal(nextClinicSlot("2026-12-31T23:59:59+08:00"), {
    date: "2027-01-01",
    time: "00:00",
  });
  equal(nextClinicSlot("2026-10-08T09:15:00-07:00"), {
    date: "2026-10-08",
    time: "09:30",
  });
});
