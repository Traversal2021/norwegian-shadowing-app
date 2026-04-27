import type { UseAudioPlayerReturn } from '../hooks/useAudioPlayer'
import { SPEED_OPTIONS } from '../hooks/useAudioPlayer'
import { formatTime } from '../utils/format'

interface Props {
  player: UseAudioPlayerReturn
}

/**
 * Audio player bar with play/pause, scrubber, and speed selector.
 * The hidden <audio> element is owned by the audioRef from useAudioPlayer.
 */
export function AudioPlayer({ player }: Props) {
  const progressPercent =
    player.duration > 0 ? (player.currentTime / player.duration) * 100 : 0

  function handleScrub(e: React.ChangeEvent<HTMLInputElement>) {
    player.seekTo(Number(e.target.value))
  }

  return (
    <div className="bg-white border-t border-gray-200 px-4 py-3 space-y-2">
      {/* Hidden native audio element — src is set by useAudioPlayer */}
      <audio ref={player.audioRef} preload="metadata" className="hidden" />

      {player.hasError && (
        <p className="text-xs text-amber-600 text-center">
          Audio not found — drop{' '}
          <code className="bg-amber-50 px-1 rounded font-mono">audio.mp3</code> into the
          lesson folder to enable playback.
        </p>
      )}

      {/* Scrubber */}
      <input
        type="range"
        min={0}
        max={player.duration || 1}
        step={0.1}
        value={player.currentTime}
        onChange={handleScrub}
        disabled={player.hasError || player.duration === 0}
        className="w-full h-1.5 accent-brand-500 cursor-pointer disabled:opacity-30"
        aria-label="Audio position"
      />

      <div className="flex items-center gap-3">
        {/* Time display */}
        <span className="text-xs text-gray-400 tabular-nums w-20 shrink-0">
          {formatTime(player.currentTime)} / {formatTime(player.duration)}
        </span>

        {/* Play / Pause */}
        <button
          onClick={player.toggle}
          disabled={player.hasError}
          className="w-10 h-10 rounded-full bg-brand-500 hover:bg-brand-600 disabled:opacity-30
                     flex items-center justify-center text-white transition-colors shrink-0"
          aria-label={player.isPlaying ? 'Pause' : 'Play'}
        >
          {player.isPlaying ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <rect x="5" y="4" width="3" height="12" rx="1" />
              <rect x="12" y="4" width="3" height="12" rx="1" />
            </svg>
          ) : (
            <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6 4l10 6-10 6V4z" />
            </svg>
          )}
        </button>

        {/* Speed selector */}
        <select
          value={player.speed}
          onChange={(e) => player.setSpeed(Number(e.target.value))}
          className="text-xs border border-gray-200 rounded px-1.5 py-1 text-gray-600
                     focus:outline-none focus:ring-1 focus:ring-brand-500"
          aria-label="Playback speed"
        >
          {SPEED_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}×
            </option>
          ))}
        </select>

        <span className="ml-auto text-xs text-gray-400 hidden sm:inline">
          Space play/pause · J/K navigate · R replay · F focus
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-0.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-500 transition-all duration-100"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  )
}
