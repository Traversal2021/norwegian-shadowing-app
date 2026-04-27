import { Link } from 'react-router-dom'
import { useLessonManifest } from '../hooks/useLessonManifest'
import { buildLibraryReviewQueue } from '../utils/reviewQueue'
import { loadLessonStudyMetadata } from '../utils/studyMetadata'

const REASON_LABELS = {
  difficult: 'Difficult segments',
  incomplete: 'Incomplete lesson',
  recent: 'Recently opened',
} as const

export function ReviewDashboard() {
  const manifest = useLessonManifest()
  const lessons = manifest.status === 'success' ? manifest.lessons : []
  const metadataByLesson = Object.fromEntries(
    lessons.map((lesson) => [lesson.id, loadLessonStudyMetadata(lesson.id)] as const),
  )
  const queue = buildLibraryReviewQueue(lessons, metadataByLesson)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <Link to="/" className="text-sm text-brand-700 hover:underline">
          Back to library
        </Link>
        <h1 className="text-xl font-bold text-gray-900 mt-2">Review Queue</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Local retrieval queue from difficult, recent, and incomplete lessons
        </p>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-3">
        {manifest.status === 'loading' && (
          <p className="text-center text-gray-400 py-12 text-sm">Loading review queue…</p>
        )}
        {manifest.status === 'error' && (
          <div className="bg-red-50 border border-red-100 text-red-600 rounded-xl p-4 text-sm">
            Could not load lessons: {manifest.message}
          </div>
        )}
        {manifest.status === 'success' && queue.length === 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 text-sm text-gray-500">
            Nothing to review yet. Start a lesson or mark segments difficult to build a queue.
          </div>
        )}
        {queue.map((item, index) => (
          <Link
            key={`${item.lessonId}-${item.reason}-${index}`}
            to={item.reason === 'difficult' ? `/lessons/${item.lessonId}?drill=difficult` : `/lessons/${item.lessonId}`}
            className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-brand-500 hover:shadow-sm transition-all"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-gray-900">{item.lessonTitle}</p>
                <p className="text-sm text-gray-500 mt-1">{REASON_LABELS[item.reason]}</p>
              </div>
              <span className="text-xs rounded-full border border-gray-200 px-2 py-0.5 text-gray-500">
                Review
              </span>
            </div>
          </Link>
        ))}
      </main>
    </div>
  )
}
