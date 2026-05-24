export interface ParsedContentColumn {
  name: string
  description: string
  frequency: string
  examples: string[]
}

export function normalizeContentColumns(items: unknown[]): ParsedContentColumn[] {
  return items.map((item, index) => normalizeContentColumn(item, index))
}

export function formatPresentationValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => formatPresentationValue(item)).join('、')
  }

  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}：${formatPresentationValue(item)}`)
      .join('\n')
  }

  return String(value ?? '')
}

function normalizeContentColumn(item: unknown, index: number): ParsedContentColumn {
  const parsed = parseJsonLikeValue(item)
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    const record = parsed as Record<string, unknown>
    return {
      name: firstString(record, ['name', 'title', 'column_name']) || `栏目 ${index + 1}`,
      description: firstString(record, ['description', 'desc', 'summary', 'content']),
      frequency: firstString(record, ['frequency', 'freq', 'cadence']),
      examples: firstStringArray(record, ['examples', 'sample_titles', 'topics', 'samples']),
    }
  }

  return {
    name: formatPresentationValue(parsed || item),
    description: '',
    frequency: '',
    examples: [],
  }
}

function parseJsonLikeValue(value: unknown): unknown {
  if (typeof value !== 'string') {
    return value
  }

  const trimmed = value.trim()
  if (!trimmed || (!trimmed.startsWith('{') && !trimmed.startsWith('['))) {
    return value
  }

  try {
    return JSON.parse(trimmed)
  } catch {
    return value
  }
}

function firstString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string') {
      return value
    }
  }
  return ''
}

function firstStringArray(record: Record<string, unknown>, keys: string[]): string[] {
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value)) {
      return value.map((item) => formatPresentationValue(item)).filter(Boolean)
    }
  }
  return []
}
