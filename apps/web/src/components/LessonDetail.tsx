import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useLesson, getActiveSegmentIndex } from '../hooks/useLesson'
import { useAudioPlayer } from '../hooks/useAudioPlayer'
import { AudioPlayer } from './AudioPlayer'
import { ShadowingControls } from './ShadowingControls'
import { TranscriptPanel } from './TranscriptPanel'
import { VocabPanel } from './VocabPanel'
import { useShadowingSession } from '../hooks/useShadowingSession'
import {
  cacheLessonForOffline,
  isLessonCached,
  removeLessonFromOfflineCache,
} from '../utils/pwa'
import { lessonAssetPath } from '../utils/paths'
import { saveLessonStudyMetadata } from '../utils/studyMetadata'
import { levelLabel } from '../utils/format'
import type { Segment } from '../types/lesson'
import { buildDifficultSegmentQueue } from '../utils/reviewQueue'
import { collectLessonVocab, vocabToCsv, vocabToJson } from '../utils/vocabExport'
import { downloadTextFile } from '../utils/download'

export function LessonDetail() {
  const { lessonId } = useParams<{ lessonId: string }>()
  const [searchParams] = useSearchParams()
  const loadState = useLesson(lessonId ?? null)
  const isDrillMode = searchParams.get('drill') === 'difficult'
  const [cached, setCached] = useState(false)

  const audioSrc =
    loadState.status === 'success'
      ? lessonAssetPath(lessonId ?? '', loadState.lesson.audioFile)
      : null

  const player = useAudioPlayer(audioSrc)

  const allSegments = useMemo(
    () => (loadState.status === 'success' ? loadState.lesson.segments : []),
    [loadState],
  )
  const session = useShadowingSession(lessonId ?? 'unknown', allSegments, player)
  const segments = useMemo(() => {
    if (loadState.status !== 'success') return []
    return isDrillMode
      ? buildDifficultSegmentQueue(loadState.lesson, session.difficultSegmentIds)
      : allSegments
  }, [allSegments, isDrillMode, loadState, session.difficultSegmentIds])

  const activeIndex = useMemo(
    () => getActiveSegmentIndex(segments, player.currentTime),
    [segments, player.currentTime],
  )

  const activeSegment = activeIndex >= 0 ? segments[activeIndex] : null
  const segmentRepeatCountRef = useRef(0)
  const pauseTimerRef = useRef<number | null>(null)

  const replaySegment = useCallback(
    (segment: Segment | null = activeSegment) => {
      if (!segment) return
      segmentRepeatCountRef.current = 0
      player.seekTo(segment.startTime)
      player.play()
    },
    [activeSegment, player],
  )

  const goToSegment = useCallback(
    (index: number, shouldPlay = player.isPlaying) => {
      const next = segments[Math.max(0, Math.min(index, segments.length - 1))]
      if (!next) return
      segmentRepeatCountRef.current = 0
      player.seekTo(next.startTime)
      if (shouldPlay) player.play()
    },
    [player, segments],
  )

  const goPrevious = useCallback(() => {
    goToSegment(activeIndex <= 0 ? 0 : activeIndex - 1)
  }, [activeIndex, goToSegment])

  const goNext = useCallback(() => {
    goToSegment(activeIndex + 1)
  }, [activeIndex, goToSegment])

  useEffect(() => {
    if (!lessonId || loadState.status !== 'success') return
    saveLessonStudyMetadata(lessonId, {
      lastOpenedAt: new Date().toISOString(),
    })
    cacheLessonForOffline(lessonId, loadState.lesson.audioFile).then(() => {
      window.setTimeout(() => {
        isLessonCached(lessonId, loadState.lesson.audioFile).then((cached) => {
          saveLessonStudyMetadata(lessonId, { cached })
          setCached(cached)
        })
      }, 1000)
    })
  }, [lessonId, loadState])

  useEffect(() => {
    if (!lessonId || loadState.status !== 'success') return
    const completed =
      loadState.lesson.durationSeconds > 0 &&
      player.currentTime >= loadState.lesson.durationSeconds * 0.9
    saveLessonStudyMetadata(lessonId, {
      started: player.currentTime > 5 || activeIndex > 0,
      completed,
      difficultCount: session.difficultSegmentIds.length,
    })
  }, [activeIndex, lessonId, loadState, player.currentTime, session.difficultSegmentIds.length])

  useEffect(() => {
    return () => {
      if (pauseTimerRef.current) window.clearTimeout(pauseTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (!activeSegment || !player.isPlaying || player.currentTime < activeSegment.endTime) return

    const repeatTarget = session.repeatMode === 'infinite' ? Infinity : session.repeatMode
    if (segmentRepeatCountRef.current + 1 < repeatTarget) {
      segmentRepeatCountRef.current += 1
      player.seekTo(activeSegment.startTime)
      player.play()
      return
    }

    segmentRepeatCountRef.current = 0
    if (!session.autoAdvance) {
      player.pause()
      player.seekTo(activeSegment.startTime)
      return
    }

    const nextIndex = activeIndex + 1
    const nextSegment = segments[nextIndex]
    if (!nextSegment) {
      player.pause()
      return
    }

    player.pause()
    if (pauseTimerRef.current) window.clearTimeout(pauseTimerRef.current)
    pauseTimerRef.current = window.setTimeout(() => {
      player.seekTo(nextSegment.startTime)
      player.play()
    }, session.pauseSec * 1000)
  }, [activeIndex, activeSegment, player, segments, session.autoAdvance, session.pauseSec, session.repeatMode])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      if (target?.tagName === 'INPUT' || target?.tagName === 'SELECT' || target?.tagName === 'TEXTAREA') {
        return
      }
      if (event.key === ' ') {
        event.preventDefault()
        player.toggle()
      } else if (event.key.toLowerCase() === 'j') {
        goPrevious()
      } else if (event.key.toLowerCase() === 'k') {
        goNext()
      } else if (event.key.toLowerCase() === 'r') {
        replaySegment()
      } else if (event.key.toLowerCase() === 'f') {
        session.toggleFocusMode()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [goNext, goPrevious, player, replaySegment, session])

  if (loadState.status === 'loading' || loadState.status === 'idle') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-400 text-sm">Loading lesson…</p>
      </div>
    )
  }

  if (loadState.status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="text-red-500 text-sm">{loadState.message}</p>
        <Link to="/" className="text-brand-600 text-sm hover:underline">
          ← Back to library
        </Link>
      </div>
    )
  }

  const { lesson } = loadState
  const { label, className: levelClass } = levelLabel(lesson.level)

  function exportLessonVocab(format: 'csv' | 'json') {
    const items = collectLessonVocab(lesson)
    downloadTextFile(
      `${lesson.id}-vocab.${format}`,
      format === 'csv' ? vocabToCsv(items) : vocabToJson(items),
      format === 'csv' ? 'text/csv' : 'application/json',
    )
  }

  async function cacheLesson() {
    await cacheLessonForOffline(lesson.id, lesson.audioFile)
    window.setTimeout(async () => {
      const next = await isLessonCached(lesson.id, lesson.audioFile)
      setCached(next)
      saveLessonStudyMetadata(lesson.id, { cached: next })
    }, 1000)
  }

  async function removeLessonCache() {
    await removeLessonFromOfflineCache(lesson.id, lesson.audioFile)
    setCached(false)
    saveLessonStudyMetadata(lesson.id, { cached: false })
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header
        className={[
          'flex items-center gap-3 px-4 py-3 border-b border-gray-200 shrink-0',
          session.focusMode ? 'hidden sm:flex' : '',
        ].join(' ')}
      >
        <Link
          to="/"
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Back to library"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-semibold text-gray-900 truncate">{lesson.title}</h1>
          <p className="text-xs text-gray-400 truncate">
            {isDrillMode ? 'Drill difficult segments' : lesson.description}
          </p>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${levelClass}`}>
          {label}
        </span>
        {lesson.alignmentMeta?.fallbackOccurred && (
          <span
            className="text-xs px-2 py-0.5 rounded-full border border-amber-300 bg-amber-50 text-amber-700 shrink-0"
            title={`Aligner: ${lesson.alignmentMeta.alignerUsed} — timestamps are approximate`}
          >
            ~ timing
          </span>
        )}
      </header>

      {!session.focusMode && (
        <div className="border-b border-gray-100 px-4 py-2 flex flex-wrap gap-2 text-xs">
          <Link
            to={isDrillMode ? `/lessons/${lesson.id}` : `/lessons/${lesson.id}?drill=difficult`}
            className="control-button"
          >
            {isDrillMode ? 'Exit drill' : 'Drill difficult'}
          </Link>
          <button onClick={() => exportLessonVocab('csv')} className="control-button">
            Export vocab CSV
          </button>
          <button onClick={() => exportLessonVocab('json')} className="control-button">
            Export vocab JSON
          </button>
          <button onClick={cacheLesson} className="control-button">
            {cached ? 'Refresh offline cache' : 'Cache lesson'}
          </button>
          <button onClick={removeLessonCache} className="control-button">
            Remove lesson cache
          </button>
          {cached && <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-700">offline</span>}
        </div>
      )}

      {/* Transcript (scrollable, fills available space) */}
      <div className="flex-1 min-h-0">
        {isDrillMode && segments.length === 0 ? (
          <div className="h-full flex items-center justify-center p-6">
            <div className="bg-white border border-gray-200 rounded-xl p-5 text-center max-w-sm">
              <p className="font-semibold text-gray-800">No difficult segments yet</p>
              <p className="text-sm text-gray-500 mt-1">
                Mark a few transcript rows difficult, then come back for a focused drill.
              </p>
            </div>
          </div>
        ) : (
          <TranscriptPanel
            segments={segments}
            activeSegmentIndex={activeIndex}
            currentTime={player.currentTime}
            autoFollow={session.autoFollow}
            focusMode={session.focusMode}
            difficultSegmentIds={session.difficultSegmentIds}
            onSegmentClick={(segment) => {
              player.seekTo(segment.startTime)
              if (segment.id === activeSegment?.id) player.play()
            }}
            onSegmentReplay={(segment) => replaySegment(segment)}
            onToggleDifficult={session.toggleDifficult}
          />
        )}
      </div>

      {/* Vocab/Grammar panel (above player) */}
      {!session.focusMode && (
        <VocabPanel
          vocab={lesson.vocabSummary ?? lesson.vocab ?? []}
          grammar={lesson.grammarSummary ?? lesson.grammar ?? []}
        />
      )}

      <ShadowingControls
        session={session}
        onPrevious={goPrevious}
        onNext={goNext}
        onReplay={() => replaySegment()}
      />

      {/* Audio player (pinned to bottom) */}
      <AudioPlayer player={player} />
    </div>
  )
}
