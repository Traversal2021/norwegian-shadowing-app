export interface LessonStudyMetadata {
  lessonId: string
  lastOpenedAt?: string
  difficultCount: number
  cached: boolean
  started: boolean
  completed: boolean
}

const PREFIX = 'norwegian-shadowing:lesson-meta:'
const SESSION_PREFIX = 'norwegian-shadowing:'
const SESSION_SUFFIX = ':session'

export function loadLessonStudyMetadata(lessonId: string): LessonStudyMetadata {
  try {
    const raw = window.localStorage.getItem(`${PREFIX}${lessonId}`)
    if (!raw) return defaultMetadata(lessonId)
    return { ...defaultMetadata(lessonId), ...(JSON.parse(raw) as Partial<LessonStudyMetadata>) }
  } catch {
    return defaultMetadata(lessonId)
  }
}

export function saveLessonStudyMetadata(lessonId: string, patch: Partial<LessonStudyMetadata>) {
  const next = { ...loadLessonStudyMetadata(lessonId), ...patch, lessonId }
  window.localStorage.setItem(`${PREFIX}${lessonId}`, JSON.stringify(next))
  return next
}

export interface StudyDataExport {
  schemaVersion: 1
  exportedAt: string
  lessonMetadata: Record<string, LessonStudyMetadata>
  sessions: Record<string, unknown>
}

export function exportLocalStudyData(): StudyDataExport {
  const lessonMetadata: Record<string, LessonStudyMetadata> = {}
  const sessions: Record<string, unknown> = {}
  for (let index = 0; index < window.localStorage.length; index++) {
    const key = window.localStorage.key(index)
    if (!key) continue
    const raw = window.localStorage.getItem(key)
    if (!raw) continue
    try {
      if (key.startsWith(PREFIX)) {
        const lessonId = key.slice(PREFIX.length)
        lessonMetadata[lessonId] = { ...defaultMetadata(lessonId), ...(JSON.parse(raw) as object) }
      } else if (key.startsWith(SESSION_PREFIX) && key.endsWith(SESSION_SUFFIX)) {
        const lessonId = key.slice(SESSION_PREFIX.length, -SESSION_SUFFIX.length)
        sessions[lessonId] = JSON.parse(raw)
      }
    } catch {
      // Skip malformed local entries rather than blocking export.
    }
  }
  return {
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    lessonMetadata,
    sessions,
  }
}

export function importLocalStudyData(data: unknown, overwrite = false): number {
  if (!isStudyDataExport(data)) return 0
  let written = 0
  Object.entries(data.lessonMetadata).forEach(([lessonId, metadata]) => {
    const key = `${PREFIX}${lessonId}`
    if (!overwrite && window.localStorage.getItem(key)) return
    window.localStorage.setItem(key, JSON.stringify({ ...defaultMetadata(lessonId), ...metadata, lessonId }))
    written += 1
  })
  Object.entries(data.sessions).forEach(([lessonId, session]) => {
    const key = `${SESSION_PREFIX}${lessonId}${SESSION_SUFFIX}`
    if (!overwrite && window.localStorage.getItem(key)) return
    window.localStorage.setItem(key, JSON.stringify(session))
    written += 1
  })
  return written
}

export function formatLastOpened(value?: string): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function defaultMetadata(lessonId: string): LessonStudyMetadata {
  return {
    lessonId,
    difficultCount: 0,
    cached: false,
    started: false,
    completed: false,
  }
}

function isStudyDataExport(value: unknown): value is StudyDataExport {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<StudyDataExport>
  return (
    candidate.schemaVersion === 1 &&
    typeof candidate.lessonMetadata === 'object' &&
    candidate.lessonMetadata !== null &&
    typeof candidate.sessions === 'object' &&
    candidate.sessions !== null
  )
}
