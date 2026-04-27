import { useState, useEffect } from 'react'
import type { Lesson } from '../types/lesson'
import { lessonAssetPath } from '../utils/paths'

export type LessonLoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; lesson: Lesson }
  | { status: 'error'; message: string }

/**
 * Fetches and parses a lesson.json from the public lessons directory.
 * lessonId maps to /lessons/{lessonId}/lesson.json
 */
export function useLesson(lessonId: string | null): LessonLoadState {
  const [state, setState] = useState<LessonLoadState>({ status: 'idle' })

  useEffect(() => {
    if (!lessonId) {
      setState({ status: 'idle' })
      return
    }

    setState({ status: 'loading' })

    const controller = new AbortController()

    fetch(lessonAssetPath(lessonId, 'lesson.json'), { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<Lesson>
      })
      .then((lesson) => {
        // Validate minimal required fields before trusting the JSON
        if (!lesson.id || !Array.isArray(lesson.segments)) {
          throw new Error('Invalid lesson.json: missing id or segments')
        }
        setState({ status: 'success', lesson })
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return
        setState({
          status: 'error',
          message: err instanceof Error ? err.message : 'Failed to load lesson',
        })
      })

    return () => controller.abort()
  }, [lessonId])

  return state
}

/** Returns the segment index whose time range contains currentTime, or -1. */
export function getActiveSegmentIndex(
  segments: Lesson['segments'],
  currentTime: number,
): number {
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i]
    if (currentTime >= seg.startTime && currentTime < seg.endTime) {
      return i
    }
  }
  // If past the last segment's start (audio still playing), keep last active
  for (let i = segments.length - 1; i >= 0; i--) {
    if (currentTime >= segments[i].startTime) return i
  }
  return -1
}
