import type { DailyReport } from "./api.ts";

/** A changed date or disposed account invalidates both stale success and failure. */
export function createReportLoader(fetchReport: (date?: string) => Promise<DailyReport>) {
  let revision = 0;
  return {
    invalidate: () => { revision++; },
    async load(date?: string): Promise<{ report: DailyReport | null; error: string | null } | null> {
      const current = ++revision;
      try {
        const report = await fetchReport(date);
        return current === revision ? { report, error: null } : null;
      } catch (error) {
        const message = (error as { message?: string })?.message || "Unable to refresh the daily report.";
        return current === revision ? { report: null, error: message } : null;
      }
    },
  };
}

const counts = ["appointments", "patients", "scheduled", "checked_in", "in_consultation", "completed", "cancelled"] as const;

function csvCell(value: string | number): string {
  let text = String(value);
  if (typeof value === "string" && /^[=+@-]/.test(text.trimStart())) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

export function dailyReportCsv(report: DailyReport): string {
  const header = ["report_date", "generated_at", "mode", "scope", "row_type", "doctor_id", "doctor_name", ...counts];
  const metadata = [report.date, report.generated_at, report.mode, report.scope];
  const rows: (string | number)[][] = [
    header,
    [...metadata, "total", "", "Total", ...counts.map(key => report.totals[key])],
    ...report.doctors.map(doctor => [
      ...metadata, "doctor", doctor.doctor_id ?? "", doctor.doctor_name, ...counts.map(key => doctor[key]),
    ]),
  ];
  return "\ufeff" + rows.map(row => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

export function dailyReportFilename(report: DailyReport): string {
  return `daily-report-${report.date}-${report.mode}-${report.scope}.csv`;
}
