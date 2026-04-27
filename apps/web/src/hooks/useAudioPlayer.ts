import { useState, useCallback, useEffect } from 'react'

export interface AudioPlayerState {
  isPlaying: boolean
  currentTime: number
  duration: number
  speed: number
  repeatSegment: boolean
  hasError: boolean
}

export interface AudioPlayerControls {
  audioRef: React.RefCallback<HTMLAudioElement>
  play: () => void
  pause: () => void
  toggle: () => void
  seekTo: (seconds: number) => void
  setSpeed: (speed: number) => void
  toggleRepeatSegment: () => void
}

export type UseAudioPlayerReturn = AudioPlayerState & AudioPlayerControls

const SPEED_OPTIONS = [0.5, 0.75, 1.0, 1.25, 1.5] as const
export { SPEED_OPTIONS }

/**
 * Manages all audio playback state via a native HTMLAudioElement ref.
 * Repeat-segment logic is intentionally kept outside this hook — the
 * component that knows the active segment bounds should call seekTo().
 */
export function useAudioPlayer(src: string | null): UseAudioPlayerReturn {
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [speed, setSpeedState] = useState(1.0)
  const [repeatSegment, setRepeatSegment] = useState(false)
  const [hasError, setHasError] = useState(false)

  const audioRef = useCallback((node: HTMLAudioElement | null) => {
    setAudioElement(node)
  }, [])

  // Wire up all audio element events
  useEffect(() => {
    if (!audioElement) return

    const updateDuration = () => {
      setDuration(Number.isFinite(audioElement.duration) ? audioElement.duration : 0)
    }
    const onTimeUpdate = () => setCurrentTime(audioElement.currentTime)
    const onPlay = () => setIsPlaying(true)
    const onPause = () => setIsPlaying(false)
    const onEnded = () => setIsPlaying(false)
    const onError = () => {
      setHasError(true)
      setIsPlaying(false)
    }

    audioElement.addEventListener('loadedmetadata', updateDuration)
    audioElement.addEventListener('canplay', updateDuration)
    audioElement.addEventListener('durationchange', updateDuration)
    audioElement.addEventListener('timeupdate', onTimeUpdate)
    audioElement.addEventListener('play', onPlay)
    audioElement.addEventListener('pause', onPause)
    audioElement.addEventListener('ended', onEnded)
    audioElement.addEventListener('error', onError)

    updateDuration()
    setCurrentTime(audioElement.currentTime)

    return () => {
      audioElement.removeEventListener('loadedmetadata', updateDuration)
      audioElement.removeEventListener('canplay', updateDuration)
      audioElement.removeEventListener('durationchange', updateDuration)
      audioElement.removeEventListener('timeupdate', onTimeUpdate)
      audioElement.removeEventListener('play', onPlay)
      audioElement.removeEventListener('pause', onPause)
      audioElement.removeEventListener('ended', onEnded)
      audioElement.removeEventListener('error', onError)
    }
  }, [audioElement])

  // Keep audio src in sync after media listeners are attached.
  useEffect(() => {
    if (!audioElement) return

    setHasError(false)
    setCurrentTime(0)
    setDuration(0)
    setIsPlaying(false)

    if (src) {
      if (audioElement.src !== new URL(src, window.location.href).href) {
        audioElement.src = src
      }
    } else {
      audioElement.removeAttribute('src')
    }
    audioElement.load()
  }, [audioElement, src])

  useEffect(() => {
    if (audioElement) audioElement.playbackRate = speed
  }, [audioElement, speed])

  const play = useCallback(() => {
    audioElement?.play().catch(() => {})
  }, [audioElement])

  const pause = useCallback(() => {
    audioElement?.pause()
  }, [audioElement])

  const toggle = useCallback(() => {
    const audio = audioElement
    if (!audio) return
    audio.paused ? audio.play().catch(() => {}) : audio.pause()
  }, [audioElement])

  const seekTo = useCallback((seconds: number) => {
    const audio = audioElement
    if (!audio) return
    audio.currentTime = seconds
    setCurrentTime(seconds)
  }, [audioElement])

  const setSpeed = useCallback((newSpeed: number) => {
    if (audioElement) audioElement.playbackRate = newSpeed
    setSpeedState(newSpeed)
  }, [audioElement])

  const toggleRepeatSegment = useCallback(() => {
    setRepeatSegment((prev) => !prev)
  }, [])

  return {
    audioRef,
    isPlaying,
    currentTime,
    duration,
    speed,
    repeatSegment,
    hasError,
    play,
    pause,
    toggle,
    seekTo,
    setSpeed,
    toggleRepeatSegment,
  }
}
