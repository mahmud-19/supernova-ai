/**
 * KST Time Utilities
 * All displayed timestamps use Asia/Seoul (UTC+9, no DST).
 * DB stores UTC; these helpers convert for display only.
 */

const KST_LOCALE = 'ko-KR';
const KST_TZ = 'Asia/Seoul';

/** Format an ISO/UTC string or Date to a KST date+time string: e.g. "2026-05-27 14:32 KST" */
export function formatKST(value: string | Date | null | undefined, opts?: { dateOnly?: boolean; showTZ?: boolean }): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);

  if (opts?.dateOnly) {
    return d.toLocaleDateString('en-CA', { timeZone: KST_TZ }); // YYYY-MM-DD
  }

  const datePart = d.toLocaleDateString('en-CA', { timeZone: KST_TZ }); // YYYY-MM-DD
  const timePart = d.toLocaleTimeString('en-GB', {
    timeZone: KST_TZ,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  const tz = opts?.showTZ !== false ? ' KST' : '';
  return `${datePart} ${timePart}${tz}`;
}

/** Format to a short KST date only: e.g. "May 27, 2026" */
export function formatKSTDate(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString('en-US', {
    timeZone: KST_TZ,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Format to a short KST time only: e.g. "14:32" */
export function formatKSTTime(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);
  return d.toLocaleTimeString('en-GB', {
    timeZone: KST_TZ,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

/** Return the current wall-clock time formatted as KST */
export function nowKST(): string {
  return formatKST(new Date());
}
