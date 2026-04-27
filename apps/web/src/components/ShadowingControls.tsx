import type { PauseMode, RepeatMode, ShadowingSessionState } from '../hooks/useShadowingSession'

interface Props {
  session: ShadowingSessionState
  onPrevious: () => void
  onNext: () => void
  onReplay: () => void
}

const REPEAT_OPTIONS: RepeatMode[] = [1, 2, 3, 5, 'infinite']
const PAUSE_OPTIONS: PauseMode[] = [0, 0.5, 1, 2]

export function ShadowingControls({ session, onPrevious, onNext, onReplay }: Props) {
  return (
    <div className="bg-gray-50 border-t border-gray-100 px-4 py-2">
      <div className="max-w-3xl mx-auto flex flex-wrap items-center gap-2 text-xs">
        <button className="control-button" onClick={onPrevious}>
          J Prev
        </button>
        <button className="control-button" onClick={onReplay}>
          R Replay
        </button>
        <button className="control-button" onClick={onNext}>
          K Next
        </button>

        <label className="ml-0 sm:ml-auto flex items-center gap-1 text-gray-500">
          Repeat
          <select
            value={session.repeatMode}
            onChange={(event) =>
              session.setRepeatMode(
                event.target.value === 'infinite'
                  ? 'infinite'
                  : (Number(event.target.value) as RepeatMode),
              )
            }
            className="rounded border border-gray-200 bg-white px-1.5 py-1"
          >
            {REPEAT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option === 'infinite' ? '∞' : `${option}×`}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1 text-gray-500">
          Gap
          <select
            value={session.pauseSec}
            onChange={(event) => session.setPauseSec(Number(event.target.value) as PauseMode)}
            className="rounded border border-gray-200 bg-white px-1.5 py-1"
          >
            {PAUSE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}s
              </option>
            ))}
          </select>
        </label>

        <button
          onClick={() => session.setAutoAdvance(!session.autoAdvance)}
          className={toggleClass(session.autoAdvance)}
          aria-pressed={session.autoAdvance}
        >
          Auto-advance
        </button>
        <button
          onClick={() => session.setAutoFollow(!session.autoFollow)}
          className={toggleClass(session.autoFollow)}
          aria-pressed={session.autoFollow}
        >
          Auto-follow
        </button>
        <button
          onClick={session.toggleFocusMode}
          className={toggleClass(session.focusMode)}
          aria-pressed={session.focusMode}
        >
          F Focus
        </button>
      </div>
    </div>
  )
}

function toggleClass(enabled: boolean) {
  return [
    'px-2 py-1 rounded border transition-colors',
    enabled
      ? 'bg-brand-100 border-brand-400 text-brand-700'
      : 'bg-white border-gray-200 text-gray-500',
  ].join(' ')
}
