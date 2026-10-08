import { createReportLoader, dailyReportCsv, dailyReportFilename } from "./report.ts";
import { saveCsvFile } from "./api.ts";
import type { DailyReport } from "./api.ts";

function equal(actual: unknown, expected: unknown) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(JSON.stringify({ actual, expected }));
}
const zero = { appointments: 0, patients: 0, scheduled: 0, checked_in: 0, in_consultation: 0, completed: 0, cancelled: 0 };
const report: DailyReport = {
  date: "2026-09-01", generated_at: "2026-09-01T08:00:00+08:00", mode: "demo", scope: "clinic",
  totals: { ...zero, appointments: 2, patients: 1, scheduled: 1, completed: 1 },
  doctors: [
    { ...zero, doctor_id: 1, doctor_name: 'Dr. Peña, "One"\nSecond line', appointments: 1, patients: 1, scheduled: 1 },
    { ...zero, doctor_id: 2, doctor_name: "\t=SUM(A1:A2)", appointments: 1, patients: 1, completed: 1 },
  ],
};

Deno.test("CSV preserves displayed totals, Unicode, quoting, newlines, and neutralizes formulas", () => {
  const csv = dailyReportCsv(report);
  equal(csv.startsWith("\ufeff"), true);
  equal(csv.includes('"total","","Total","2","1","1","0","0","1","0"'), true);
  equal(csv.includes('"Dr. Peña, ""One""\nSecond line"'), true);
  equal(csv.includes('"\'\t=SUM(A1:A2)"'), true);
  equal(dailyReportFilename(report), "daily-report-2026-09-01-demo-clinic.csv");
  for (const name of ["+SUM(A1)", "-1+2", "@SUM(A1)", " =1"]) {
    const changed = { ...report, doctors: [{ ...report.doctors[0], doctor_name: name }] };
    equal(dailyReportCsv(changed).includes('"\'' + name + '"'), true);
  }
});

Deno.test("an empty date still exports a zero total row and report metadata", () => {
  const csv = dailyReportCsv({ ...report, totals: zero, doctors: [] });
  equal(csv.split("\r\n").length, 3);
  equal(csv.includes('"2026-09-01","2026-09-01T08:00:00+08:00","demo","clinic","total"'), true);
  equal(csv.includes('"Total","0","0","0","0","0","0","0"'), true);
});

Deno.test("a late date response cannot replace the current report", async () => {
  let release!: (value: DailyReport) => void;
  const loader = createReportLoader(date => date === "2026-09-01"
    ? new Promise(resolve => release = resolve)
    : Promise.resolve({ ...report, date: "2026-09-02" }));
  const previous = loader.load("2026-09-01");
  equal((await loader.load("2026-09-02"))?.report?.date, "2026-09-02");
  release(report);
  equal(await previous, null);
});

Deno.test("account disposal discards stale success and stale errors", async () => {
  let release!: (value: DailyReport) => void;
  let reject!: (error: Error) => void;
  const loader = createReportLoader(() => new Promise((resolve, fail) => { release = resolve; reject = fail; }));
  const oldAccount = loader.load();
  loader.invalidate();
  release(report);
  equal(await oldAccount, null);
  const oldError = loader.load();
  loader.invalidate();
  reject(new Error("Old account failed"));
  equal(await oldError, null);
});

Deno.test("current failures stay visible and Today omits a fixed date", async () => {
  const dates: (string | undefined)[] = [];
  const loader = createReportLoader(date => { dates.push(date); return Promise.reject(new Error("Synthetic report failure")); });
  equal(await loader.load(), { report: null, error: "Synthetic report failure" });
  equal(dates, [undefined]);
});

Deno.test("native CSV save cancellation and write failures never report success", async () => {
  const host = { save_report_csv: (_name: string, _content: string) => Promise.resolve({ status: "cancelled" as const }) };
  Object.defineProperty(globalThis, "window", { configurable: true, value: { pywebview: { api: host }, __DESKTOP_HOST__: true } });
  equal(await saveCsvFile(dailyReportFilename(report), dailyReportCsv(report)), "cancelled");
  Object.assign(host, { save_report_csv: () => Promise.reject(new Error("Synthetic save failure")) });
  let message = "";
  try { await saveCsvFile(dailyReportFilename(report), dailyReportCsv(report)); } catch (error) { message = (error as Error).message; }
  equal(message, "Synthetic save failure");
});
