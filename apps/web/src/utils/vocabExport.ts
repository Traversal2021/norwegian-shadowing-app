import type { Lesson, VocabItem } from '../types/lesson'

export interface ExportedVocabItem extends VocabItem {
  lessonId: string
  lessonTitle: string
}

export function collectLessonVocab(lesson: Lesson): ExportedVocabItem[] {
  const vocab = lesson.vocabSummary ?? lesson.vocab ?? []
  return vocab.map((item) => ({
    lessonId: lesson.id,
    lessonTitle: lesson.title,
    word: item.word,
    definition: item.definition,
    example: item.example,
  }))
}

export function vocabToJson(items: ExportedVocabItem[]): string {
  return JSON.stringify(items, null, 2)
}

export function vocabToCsv(items: ExportedVocabItem[]): string {
  const header = ['lessonId', 'lessonTitle', 'word', 'definition', 'example']
  const rows = items.map((item) =>
    [item.lessonId, item.lessonTitle, item.word, item.definition, item.example ?? ''].map(csvEscape).join(','),
  )
  return [header.join(','), ...rows].join('\n') + '\n'
}

function csvEscape(value: string): string {
  if (!/[",\n]/.test(value)) return value
  return `"${value.replace(/"/g, '""')}"`
}
