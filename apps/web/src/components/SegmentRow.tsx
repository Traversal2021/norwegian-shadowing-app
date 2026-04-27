import { useEffect, useRef } from 'react'
import type { Segment } from '../types/lesson'

interface Props {
  segment: Segment
  isActive: boolean
  isCompleted: boolean
  isDifficult: boolean
  showGloss: boolean
  autoFollow: boolean
  focusMode: boolean
  currentTime: number
  onClick: () => void
  onReplay: () => void
  onToggleDifficult: () => void
}

/**
 * One row in the transcript panel. Renders tokens with optional inline gloss
 * and scrolls itself into view when it becomes active.
 */
export function SegmentRow({
  segment,
  isActive,
  isCompleted,
  isDifficult,
  showGloss,
  autoFollow,
  focusMode,
  currentTime,
  onClick,
  onReplay,
  onToggleDifficult,
}: Props) {
  const rowRef = useRef<HTMLDivElement>(null)

  // Auto-scroll active segment into view
  useEffect(() => {
    if (autoFollow && isActive && rowRef.current) {
      rowRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [autoFollow, isActive])

  return (
    <div
      ref={rowRef}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      aria-label={`Seek to segment ${segment.id}`}
      className={[
        'px-4 py-3 rounded-lg cursor-pointer transition-colors duration-150 select-none',
        'hover:bg-brand-50',
        isActive
          ? 'bg-brand-100 border-l-4 border-brand-500'
          : isCompleted
            ? 'bg-gray-50 border-l-4 border-gray-200 opacity-75'
            : 'border-l-4 border-transparent',
        isDifficult ? 'ring-1 ring-amber-300' : '',
      ].join(' ')}
    >
      <p
        className={[
          'leading-relaxed flex flex-wrap gap-x-1',
          focusMode ? 'text-xl sm:text-2xl' : 'text-base',
        ].join(' ')}
      >
        {segment.tokens.map((token, i) => (
          <span key={i} className="relative">
            <span
              className={[
                isActive ? 'font-medium' : '',
                isTokenActive(token, currentTime)
                  ? 'text-white bg-brand-500 rounded px-0.5'
                  : isActive
                    ? 'text-brand-700'
                    : isCompleted
                      ? 'text-gray-500'
                      : 'text-gray-800',
              ].join(' ')}
            >
              {token.text}
            </span>
            {showGloss && token.gloss && (
              <span className="ml-0.5 text-xs text-amber-600 font-normal align-super">
                ({token.gloss})
              </span>
            )}
          </span>
        ))}
      </p>
      {segment.translation && (
        <p className="mt-1 text-sm text-gray-400 italic">{segment.translation}</p>
      )}
      <div className="mt-2 flex items-center gap-2 text-xs">
        <button
          onClick={(event) => {
            event.stopPropagation()
            onReplay()
          }}
          className="text-brand-600 hover:underline"
        >
          Replay
        </button>
        <button
          onClick={(event) => {
            event.stopPropagation()
            onToggleDifficult()
          }}
          className={isDifficult ? 'text-amber-700 font-medium' : 'text-gray-400 hover:text-amber-600'}
        >
          {isDifficult ? 'Marked difficult' : 'Mark difficult'}
        </button>
      </div>
    </div>
  )
}

function isTokenActive(token: Segment['tokens'][number], currentTime: number) {
  return token.start !== undefined && token.end !== undefined && currentTime >= token.start && currentTime < token.end
}
