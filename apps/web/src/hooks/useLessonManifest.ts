import { useEffect, useState } from 'react'
import type { LessonManifestEntry } from '../types/lesson'
import { appPath } from '../utils/paths'

export type LessonManifestState =
  | { status: 'loading' }
  | { status: 'success'; lessons: LessonManifestEntry[] }
  | { status: 'error'; message: string }

export function useLessonManifest(): LessonManifestState {
  const [state, setState] = useState<LessonManifestState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    fetch(appPath('lessons/index.json'), { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<LessonManifestEntry[]>
      })
      .then((lessons) => {
        if (!Array.isArray(lessons)) {
          throw new Error('Invalid lesson manifest: expected an array')
        }
        setState({ status: 'success', lessons })
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return
        setState({
          status: 'error',
          message: err instanceof Error ? err.message : 'Failed to load lesson manifest',
        })
      })

    return () => controller.abort()
  }, [])

  return state
}
