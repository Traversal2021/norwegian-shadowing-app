import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Segment } from '../types/lesson'
import type { UseAudioPlayerReturn } from './useAudioPlayer'

export type RepeatMode = 1 | 2 | 3 | 5 | 'infinite'
export type PauseMode = 0 | 0.5 | 1 | 2

export interface ShadowingSessionState {
  repeatMode: RepeatMode
  pauseSec: PauseMode
  autoAdvance: boolean
  focusMode: boolean
  autoFollow: boolean
  difficultSegmentIds: string[]
  setRepeatMode: (mode: RepeatMode) => void
  setPauseSec: (pause: PauseMode) => void
  setAutoAdvance: (enabled: boolean) => void
  setFocusMode: (enabled: boolean) => void
  toggleFocusMode: () => void
  setAutoFollow: (enabled: boolean) => void
  toggleDifficult: (segmentId: string) => void
  isDifficult: (segmentId: string) => boolean
}

interface PersistedShadowingState {
  lastPlaybackPosition?: number
  playbackSpeed?: number
  repeatMode?: RepeatMode
  pauseSec?: PauseMode
  autoAdvance?: boolean
  focusMode?: boolean
  autoFollow?: boolean
  difficultSegmentIds?: string[]
}

const REPEAT_MODES: RepeatMode[] = [1, 2, 3, 5, 'infinite']
const PAUSE_MODES: PauseMode[] = [0, 0.5, 1, 2]

export function useShadowingSession(
  lessonId: string,
  segments: Segment[],
  player: UseAudioPlayerReturn,
): ShadowingSessionState {
  const storageKey = `norwegian-shadowing:${lessonId}:session`
  const initial = useMemo(() => loadSessionState(storageKey), [storageKey])

  const [repeatMode, setRepeatModeState] = useState<RepeatMode>(initial.repeatMode ?? 1)
  const [pauseSec, setPauseSecState] = useState<PauseMode>(initial.pauseSec ?? 0)
  const [autoAdvance, setAutoAdvanceState] = useState(initial.autoAdvance ?? true)
  const [focusMode, setFocusModeState] = useState(initial.focusMode ?? false)
  const [autoFollow, setAutoFollowState] = useState(initial.autoFollow ?? true)
  const [difficultSegmentIds, setDifficultSegmentIds] = useState<string[]>(
    initial.difficultSegmentIds ?? [],
  )
  const lastSavedSecondRef = useRef(Math.floor(initial.lastPlaybackPosition ?? 0))

  useEffect(() => {
    if (initial.playbackSpeed) player.setSpeed(initial.playbackSpeed)
    if (initial.lastPlaybackPosition && segments.length > 0) {
      player.seekTo(initial.lastPlaybackPosition)
    }
  }, [initial.lastPlaybackPosition, initial.playbackSpeed, player, segments.length])

  useEffect(() => {
    const currentSecond = Math.floor(player.currentTime)
    const positionChangedEnough = Math.abs(currentSecond - lastSavedSecondRef.current) >= 5
    const timeout = window.setTimeout(() => {
      lastSavedSecondRef.current = currentSecond
      saveSessionState(storageKey, {
        lastPlaybackPosition: player.currentTime,
        playbackSpeed: player.speed,
        repeatMode,
        pauseSec,
        autoAdvance,
        focusMode,
        autoFollow,
        difficultSegmentIds,
      })
    }, positionChangedEnough ? 250 : 1000)
    return () => window.clearTimeout(timeout)
  }, [
    autoAdvance,
    autoFollow,
    difficultSegmentIds,
    focusMode,
    pauseSec,
    player.currentTime,
    player.speed,
    repeatMode,
    storageKey,
  ])

  useEffect(() => {
    const handlePageHide = () => {
      saveSessionState(storageKey, {
        lastPlaybackPosition: player.currentTime,
        playbackSpeed: player.speed,
        repeatMode,
        pauseSec,
        autoAdvance,
        focusMode,
        autoFollow,
        difficultSegmentIds,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [
    autoAdvance,
    autoFollow,
    difficultSegmentIds,
    focusMode,
    pauseSec,
    player.currentTime,
    player.speed,
    repeatMode,
    storageKey,
  ])

  const setRepeatMode = useCallback((mode: RepeatMode) => {
    setRepeatModeState(REPEAT_MODES.includes(mode) ? mode : 1)
  }, [])

  const setPauseSec = useCallback((pause: PauseMode) => {
    setPauseSecState(PAUSE_MODES.includes(pause) ? pause : 0)
  }, [])

  const setAutoAdvance = useCallback((enabled: boolean) => {
    setAutoAdvanceState(enabled)
  }, [])

  const setFocusMode = useCallback((enabled: boolean) => {
    setFocusModeState(enabled)
  }, [])

  const toggleFocusMode = useCallback(() => {
    setFocusModeState((enabled) => !enabled)
  }, [])

  const setAutoFollow = useCallback((enabled: boolean) => {
    setAutoFollowState(enabled)
  }, [])

  const toggleDifficult = useCallback((segmentId: string) => {
    setDifficultSegmentIds((ids) =>
      ids.includes(segmentId) ? ids.filter((id) => id !== segmentId) : [...ids, segmentId],
    )
  }, [])

  const isDifficult = useCallback(
    (segmentId: string) => difficultSegmentIds.includes(segmentId),
    [difficultSegmentIds],
  )

  return {
    repeatMode,
    pauseSec,
    autoAdvance,
    focusMode,
    autoFollow,
    difficultSegmentIds,
    setRepeatMode,
    setPauseSec,
    setAutoAdvance,
    setFocusMode,
    toggleFocusMode,
    setAutoFollow,
    toggleDifficult,
    isDifficult,
  }
}

export function loadSessionState(storageKey: string): PersistedShadowingState {
  try {
    const raw = window.localStorage.getItem(storageKey)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as PersistedShadowingState
    return {
      lastPlaybackPosition:
        typeof parsed.lastPlaybackPosition === 'number' ? parsed.lastPlaybackPosition : undefined,
      playbackSpeed: typeof parsed.playbackSpeed === 'number' ? parsed.playbackSpeed : undefined,
      repeatMode: isRepeatMode(parsed.repeatMode) ? parsed.repeatMode : undefined,
      pauseSec: isPauseMode(parsed.pauseSec) ? parsed.pauseSec : undefined,
      autoAdvance: typeof parsed.autoAdvance === 'boolean' ? parsed.autoAdvance : undefined,
      focusMode: typeof parsed.focusMode === 'boolean' ? parsed.focusMode : undefined,
      autoFollow: typeof parsed.autoFollow === 'boolean' ? parsed.autoFollow : undefined,
      difficultSegmentIds: Array.isArray(parsed.difficultSegmentIds)
        ? parsed.difficultSegmentIds.filter((id) => typeof id === 'string')
        : undefined,
    }
  } catch {
    return {}
  }
}

export function saveSessionState(storageKey: string, state: PersistedShadowingState) {
  window.localStorage.setItem(storageKey, JSON.stringify(state))
}

function isRepeatMode(value: unknown): value is RepeatMode {
  return REPEAT_MODES.includes(value as RepeatMode)
}

function isPauseMode(value: unknown): value is PauseMode {
  return PAUSE_MODES.includes(value as PauseMode)
}
