import { Link } from 'react-router-dom'
import { useMemo, useRef, useEffect, useState } from 'react'
import { useLessonManifest } from '../hooks/useLessonManifest'
import type { Lesson, LessonManifestEntry } from '../types/lesson'
import { levelLabel, formatTime } from '../utils/format'
import { clearLessonAssetCache, isLessonCached } from '../utils/pwa'
import {
  exportLocalStudyData,
  formatLastOpened,
  importLocalStudyData,
  loadLessonStudyMetadata,
  saveLessonStudyMetadata,
  type LessonStudyMetadata,
} from '../utils/studyMetadata'
import {
  filterAndSortLessons,
  type LibraryFilter,
  type LibrarySort,
} from '../utils/libraryFilters'
import { buildLibraryReviewQueue } from '../utils/reviewQueue'
import { downloadTextFile } from '../utils/download'
import { collectLessonVocab, vocabToCsv, vocabToJson } from '../utils/vocabExport'
import { lessonAssetPath } from '../utils/paths'

function LessonCard({ lesson }: { lesson: LessonManifestEntry }) {
  const { label, className: levelClass } = levelLabel(lesson.level ?? 'unknown')
  const [metadata, setMetadata] = useState<LessonStudyMetadata>(() =>
    loadLessonStudyMetadata(lesson.id),
  )
  const description =
    lesson.description || `${lesson.source}${lesson.tags.length ? ` • ${lesson.tags.join(', ')}` : ''}`

  useEffect(() => {
    setMetadata(loadLessonStudyMetadata(lesson.id))
    isLessonCached(lesson.id).then((cached) => {
      setMetadata(saveLessonStudyMetadata(lesson.id, { cached }))
    })
  }, [lesson.id])

  const lastOpened = formatLastOpened(metadata.lastOpenedAt)

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-brand-500
                 hover:shadow-sm transition-all duration-150 active:scale-[0.99]"
    >
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-base font-semibold text-gray-900 leading-snug">{lesson.title}</h2>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${levelClass}`}>
          {label}
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-500 leading-relaxed">{description}</p>
      <p className="mt-3 text-xs text-gray-400">
        {formatTime(lesson.durationSec)} min • {lesson.segmentCount} segments
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
        {metadata.completed && <Badge label="completed" tone="green" />}
        {!metadata.completed && metadata.started && <Badge label="started" tone="blue" />}
        {lastOpened && <Badge label={`opened ${lastOpened}`} tone="gray" />}
        {metadata.difficultCount > 0 && (
          <Badge label={`${metadata.difficultCount} difficult`} tone="amber" />
        )}
        {metadata.cached && <Badge label="offline" tone="green" />}
      </div>
    </Link>
  )
}

function Badge({ label, tone }: { label: string; tone: 'green' | 'blue' | 'gray' | 'amber' }) {
  const classes = {
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    blue: 'bg-brand-50 text-brand-700 border-brand-100',
    gray: 'bg-gray-50 text-gray-500 border-gray-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
  }
  return <span className={`rounded-full border px-2 py-0.5 ${classes[tone]}`}>{label}</span>
}

export function LessonLibrary() {
  const manifest = useLessonManifest()
  const lessons = manifest.status === 'success' ? manifest.lessons : []
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<LibraryFilter>('all')
  const [sort, setSort] = useState<LibrarySort>('title')
  const [metadataVersion, setMetadataVersion] = useState(0)
  const metadataByLesson = useMemo(() => {
    const entries = lessons.map((lesson) => [lesson.id, loadLessonStudyMetadata(lesson.id)] as const)
    return Object.fromEntries(entries)
  }, [lessons, metadataVersion])
  const visibleLessons = useMemo(
    () => filterAndSortLessons(lessons, metadataByLesson, { query, filter, sort }),
    [filter, lessons, metadataByLesson, query, sort],
  )
  const reviewQueue = useMemo(
    () => buildLibraryReviewQueue(lessons, metadataByLesson),
    [lessons, metadataByLesson],
  )

  async function exportAllVocab(format: 'csv' | 'json') {
    const lessonPayloads = await Promise.all(
      lessons.map(async (lesson) => {
        const response = await fetch(lessonAssetPath(lesson.id, 'lesson.json'))
        if (!response.ok) return null
        return (await response.json()) as Lesson
      }),
    )
    const items = lessonPayloads.flatMap((lesson) => (lesson ? collectLessonVocab(lesson) : []))
    downloadTextFile(
      `norwegian-shadowing-vocab.${format}`,
      format === 'csv' ? vocabToCsv(items) : vocabToJson(items),
      format === 'csv' ? 'text/csv' : 'application/json',
    )
  }

  function exportStudyData() {
    downloadTextFile(
      'norwegian-shadowing-study-data.json',
      JSON.stringify(exportLocalStudyData(), null, 2),
      'application/json',
    )
  }

  async function importStudyData(file: File | undefined) {
    if (!file) return
    try {
      const text = await file.text()
      const overwrite = window.confirm('Overwrite existing local study state where keys overlap? Cancel keeps existing values.')
      const written = importLocalStudyData(JSON.parse(text), overwrite)
      window.alert(`Imported ${written} local study records.`)
      setMetadataVersion((version) => version + 1)
    } catch {
      window.alert('Could not import study data. Please choose a valid JSON export file.')
    }
  }

  async function clearLessonCaches() {
    if (!window.confirm('Remove cached lesson JSON, captions, and audio? App shell cache stays installed.')) return
    await clearLessonAssetCache()
    lessons.forEach((lesson) => saveLessonStudyMetadata(lesson.id, { cached: false }))
    setMetadataVersion((version) => version + 1)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <h1 className="text-xl font-bold text-gray-900">Norwegian Shadowing</h1>
        <p className="text-sm text-gray-400 mt-0.5">Commute-friendly language practice</p>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-4">
        <section className="bg-white rounded-xl border border-gray-200 p-3 space-y-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, source, or tags"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value as LibraryFilter)}
              className="rounded-lg border border-gray-200 px-2 py-2 text-sm text-gray-600"
            >
              <option value="all">All lessons</option>
              <option value="started">Started</option>
              <option value="completed">Completed</option>
              <option value="cached">Offline</option>
              <option value="difficult">Has difficult</option>
            </select>
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as LibrarySort)}
              className="rounded-lg border border-gray-200 px-2 py-2 text-sm text-gray-600"
            >
              <option value="title">Sort by title</option>
              <option value="lastOpened">Last opened</option>
              <option value="recentlyAdded">Recently added</option>
              <option value="difficultCount">Difficult count</option>
            </select>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Link to="/review" className="control-button">
              Review queue ({reviewQueue.length})
            </Link>
            <button onClick={() => exportAllVocab('csv')} className="control-button">
              Export vocab CSV
            </button>
            <button onClick={() => exportAllVocab('json')} className="control-button">
              Export vocab JSON
            </button>
            <button onClick={exportStudyData} className="control-button">
              Export study data
            </button>
            <button onClick={() => fileInputRef.current?.click()} className="control-button">
              Import study data
            </button>
            <button onClick={clearLessonCaches} className="control-button">
              Clear lesson cache
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(event) => importStudyData(event.target.files?.[0])}
            />
          </div>
        </section>

        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          Lessons ({visibleLessons.length}/{lessons.length})
        </h2>

        {manifest.status === 'loading' && (
          <p className="text-center text-gray-400 py-12 text-sm">Loading lessons…</p>
        )}

        {manifest.status === 'error' && (
          <div className="bg-red-50 border border-red-100 text-red-600 rounded-xl p-4 text-sm">
            Could not load lesson manifest: {manifest.message}
          </div>
        )}

        {manifest.status === 'success' &&
          visibleLessons.map((lesson) => <LessonCard key={lesson.id} lesson={lesson} />)}

        {manifest.status === 'success' && visibleLessons.length === 0 && (
          <p className="text-center text-gray-400 py-12 text-sm">No lessons yet.</p>
        )}
      </main>
    </div>
  )
}
