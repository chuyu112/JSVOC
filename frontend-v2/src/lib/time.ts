const BEIJING_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: "Asia/Shanghai",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
};

const COMPACT_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: "Asia/Shanghai",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
};

function normalizeToUTC(value: string | Date): Date {
  if (value instanceof Date) return value;
  const trimmed = value.trim();
  // Backend stores naive UTC datetimes; append Z so browsers treat them as UTC.
  const normalized = /[Zz]$|([+-]\d{2}:?\d{2})$/.test(trimmed) ? trimmed : `${trimmed}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? new Date(value) : date;
}

export function formatBeijingTime(value: string | Date | null | undefined): string {
  if (!value) return "-";
  const date = normalizeToUTC(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("zh-CN", BEIJING_OPTIONS);
}

export function formatCompactBeijingTime(value: string | Date | null | undefined): string {
  if (!value) return "-";
  const date = normalizeToUTC(value);
  if (Number.isNaN(date.getTime())) return "-";
  const parts = new Intl.DateTimeFormat("zh-CN", COMPACT_OPTIONS).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("month")}/${get("day")} ${get("hour")}:${get("minute")}`;
}

export function formatBeijingDate(value: string | Date | null | undefined): string {
  if (!value) return "-";
  const date = normalizeToUTC(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}
