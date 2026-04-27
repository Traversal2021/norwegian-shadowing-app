import { useState } from 'react'
import type { Lesson, Segment } from '../types/lesson'
import { SegmentRow } from './SegmentRow'

interface Props {
  segments: Lesson['segments']
  activeSegmentIndex: number
  currentTime: number
  autoFollow: boolean
  focusMode: boolean
  difficultSegmentIds: string[]
  onSegmentClick: (segment: Segment) => void
  onSegmentReplay: (segment: Segment) => void
  onToggleDifficult: (segmentId: string) => void
}

export function TranscriptPanel({
  segments,
  activeSegmentIndex,
  currentTime,
  autoFollow,
  focusMode,
  difficultSegmentIds,
  onSegmentClick,
  onSegmentReplay,
  onToggleDifficult,
}: Props) {
  const [showGloss, setShowGloss] = useState(true)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 shrink-0">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Transcript
        </h2>
        <button
          onClick={() => setShowGloss((v) => !v)}
          className={[
            'text-xs px-2 py-1 rounded-full border transition-colors',
            showGloss
              ? 'bg-amber-50 border-amber-300 text-amber-700'
              : 'bg-gray-50 border-gray-200 text-gray-500',
          ].join(' ')}
          aria-pressed={showGloss}
        >
          {showGloss ? 'Hide glosses' : 'Show glosses'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2 space-y-1">
        {segments.map((segment, index) => (
          <SegmentRow
            key={segment.id}
            segment={segment}
            isActive={index === activeSegmentIndex}
            isCompleted={index < activeSegmentIndex}
            isDifficult={difficultSegmentIds.includes(segment.id)}
            showGloss={showGloss}
            autoFollow={autoFollow}
            focusMode={focusMode}
            currentTime={currentTime}
            onClick={() => onSegmentClick(segment)}
            onReplay={() => onSegmentReplay(segment)}
            onToggleDifficult={() => onToggleDifficult(segment.id)}
          />
        ))}
      </div>
    </div>
  )
}
