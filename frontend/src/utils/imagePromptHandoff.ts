export type ImagePromptHandoffMode = 'text' | 'image'

export interface ImagePromptHandoff {
  mode: ImagePromptHandoffMode
  prompt: string
}

type QueryValue = string | null | Array<string | null> | undefined
type ImagePromptHandoffQuery = Record<string, string>

export function buildImagePromptHandoffQuery(
  prompt: string,
  mode: ImagePromptHandoffMode,
): ImagePromptHandoffQuery {
  return {
    mode,
    prompt: prompt.trim(),
  }
}

export function readImagePromptHandoffQuery(query: Record<string, QueryValue>): ImagePromptHandoff | null {
  const prompt = firstQueryValue(query.prompt).trim()
  if (!prompt) return null

  const mode = firstQueryValue(query.mode) === 'image' ? 'image' : 'text'
  return { mode, prompt }
}

function firstQueryValue(value: QueryValue): string {
  if (Array.isArray(value)) return value[0] || ''
  return value || ''
}
