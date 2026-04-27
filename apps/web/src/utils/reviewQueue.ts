import type { Lesson, LessonManifestEntry, Segment } from '../types/lesson'
import type { LessonStudyMetadata } from './studyMetadata'

export interface ReviewQueueItem {
  lessonId: string
  lessonTitle: string
  reason: 'difficult' | 'recent' | 'incomplete'
  segmentId?: string
  segmentText?: string
}

export function buildDifficultSegmentQueue(
  lesson: Lesson,
  difficultSegmentIds: string[],
): Segment[] {
  const difficult = new Set(difficultSegmentIds)
  return lesson.segments.filter((segment) => difficult.has(segment.id))
}

export function buildLibraryReviewQueue(
  lessons: LessonManifestEntry[],
  metadataByLesson: Record<string, LessonStudyMetadata>,
): ReviewQueueItem[] {
  const queue: ReviewQueueItem[] = []
  lessons.forEach((lesson) => {
    const metadata = metadataByLesson[lesson.id]
    if (!metadata) return
    if (metadata.difficultCount > 0) {
      queue.push({
        lessonId: lesson.id,
        lessonTitle: lesson.title,
        reason: 'difficult',
      })
    }
    if (metadata.started && !metadata.completed) {
      queue.push({
        lessonId: lesson.id,
        lessonTitle: lesson.title,
        reason: 'incomplete',
      })
    }
    if (metadata.lastOpenedAt && !metadata.completed) {
      queue.push({
        lessonId: lesson.id,
        lessonTitle: lesson.title,
        reason: 'recent',
      })
    }
  })
  return queue.sort((a, b) => reasonRank(a.reason) - reasonRank(b.reason))
}

export function segmentText(segment: Segment): string {
  return segment.tokens.map((token) => token.text).join(' ').replace(/\s+([.,!?;:])/g, '$1')
}

function reasonRank(reason: ReviewQueueItem['reason']): number {
  if (reason === 'difficult') return 0
  if (reason === 'incomplete') return 1
  return 2
}
