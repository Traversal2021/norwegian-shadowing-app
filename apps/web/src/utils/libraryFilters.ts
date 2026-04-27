import type { LessonManifestEntry } from '../types/lesson'
import type { LessonStudyMetadata } from './studyMetadata'

export type LibraryFilter = 'all' | 'started' | 'completed' | 'cached' | 'difficult'
export type LibrarySort = 'title' | 'lastOpened' | 'recentlyAdded' | 'difficultCount'

export interface LibraryDashboardState {
  query: string
  filter: LibraryFilter
  sort: LibrarySort
}

export function filterAndSortLessons(
  lessons: LessonManifestEntry[],
  metadataByLesson: Record<string, LessonStudyMetadata>,
  state: LibraryDashboardState,
): LessonManifestEntry[] {
  const query = state.query.trim().toLowerCase()
  return lessons
    .filter((lesson) => matchesQuery(lesson, query))
    .filter((lesson) => matchesFilter(metadataByLesson[lesson.id], state.filter))
    .sort((a, b) => compareLessons(a, b, metadataByLesson, state.sort))
}

function matchesQuery(lesson: LessonManifestEntry, query: string): boolean {
  if (!query) return true
  return [lesson.title, lesson.source, ...(lesson.tags ?? [])]
    .filter(Boolean)
    .some((value) => value.toLowerCase().includes(query))
}

function matchesFilter(metadata: LessonStudyMetadata | undefined, filter: LibraryFilter): boolean {
  if (filter === 'all') return true
  if (!metadata) return false
  if (filter === 'started') return metadata.started
  if (filter === 'completed') return metadata.completed
  if (filter === 'cached') return metadata.cached
  if (filter === 'difficult') return metadata.difficultCount > 0
  return true
}

function compareLessons(
  a: LessonManifestEntry,
  b: LessonManifestEntry,
  metadataByLesson: Record<string, LessonStudyMetadata>,
  sort: LibrarySort,
): number {
  if (sort === 'title') return a.title.localeCompare(b.title)
  if (sort === 'difficultCount') {
    return (metadataByLesson[b.id]?.difficultCount ?? 0) - (metadataByLesson[a.id]?.difficultCount ?? 0)
  }
  if (sort === 'lastOpened') {
    return dateValue(metadataByLesson[b.id]?.lastOpenedAt) - dateValue(metadataByLesson[a.id]?.lastOpenedAt)
  }
  if (sort === 'recentlyAdded') {
    return dateValue(b.createdAt) - dateValue(a.createdAt)
  }
  return 0
}

function dateValue(value?: string): number {
  if (!value) return 0
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 0 : date.getTime()
}
