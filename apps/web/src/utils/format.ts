/** Formats seconds into mm:ss display string. */
export function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

/** Maps lesson level to a human-readable label and color class. */
export function levelLabel(level: 'unknown' | 'beginner' | 'intermediate' | 'advanced'): {
  label: string
  className: string
} {
  switch (level) {
    case 'unknown':
      return { label: 'Unknown', className: 'bg-gray-100 text-gray-700' }
    case 'beginner':
      return { label: 'Beginner', className: 'bg-green-100 text-green-800' }
    case 'intermediate':
      return { label: 'Intermediate', className: 'bg-yellow-100 text-yellow-800' }
    case 'advanced':
      return { label: 'Advanced', className: 'bg-red-100 text-red-800' }
  }
}
