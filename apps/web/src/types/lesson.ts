/**
 * Core domain types for the Norwegian Shadowing app.
 * These types are shared across the web app and inform the Python pipeline models.
 */

/** One word or punctuation unit in a segment. */
export interface Token {
  /** The Norwegian surface form as it appears in the original text. */
  text: string;
  /** Optional English gloss for difficult or non-obvious vocabulary. */
  gloss?: string;
  /** Optional token start time in seconds, when real alignment provides it. */
  start?: number;
  /** Optional token end time in seconds, when real alignment provides it. */
  end?: number;
  /** Optional aligner confidence for this token. */
  confidence?: number;
}

/**
 * One time-aligned chunk of audio and text.
 * Corresponds to one row in the transcript panel.
 */
export interface Segment {
  /** Stable unique id within the lesson, e.g. "s1", "s2". */
  id: string;
  /** Preferred schema v2 plain visible text. */
  textPlain?: string;
  /** Preferred schema v2 canonical annotated text. */
  textAnnotated?: string;
  /** Preferred schema v2 segment start time. */
  start?: number;
  /** Preferred schema v2 segment end time. */
  end?: number;
  /** Segment start time in seconds (from audio track start). */
  startTime: number;
  /** Segment end time in seconds. */
  endTime: number;
  /** Ordered list of tokens that make up this segment's Norwegian text. */
  tokens: Token[];
  /** Optional full English translation of the segment. */
  translation?: string;
}

/** One entry in the lesson's vocabulary summary. */
export interface VocabItem {
  /** The Norwegian word or phrase. */
  word: string;
  /** English definition. */
  definition: string;
  /** Optional example sentence in Norwegian. */
  example?: string;
}

/** One entry in the lesson's grammar notes. */
export interface GrammarItem {
  /** Short descriptive title, e.g. "Common gender nouns with -et". */
  title: string;
  /** Plain-text explanation. */
  explanation: string;
  /** Optional Norwegian example illustrating the pattern. */
  example?: string;
}

/** Top-level lesson object as stored in lesson.json. */
export interface Lesson {
  /** Preferred schema version for newly processed lessons. */
  schemaVersion?: number;
  /** Stable unique lesson id, matches the folder name in public/lessons/. */
  id: string;
  /** Human-readable lesson title in Norwegian or English. */
  title: string;
  /** Source label from lesson metadata. */
  source?: string;
  /** Lesson language code. */
  language?: string;
  /** Short description shown on the lesson library card. */
  description: string;
  /** Approximate difficulty level. */
  level: 'unknown' | 'beginner' | 'intermediate' | 'advanced';
  /** Metadata tags. */
  tags?: string[];
  /** Total audio duration in seconds. */
  durationSeconds: number;
  /**
   * Filename of the audio file relative to the lesson folder.
   * e.g. "audio.mp3" → fetched from /lessons/{id}/audio.mp3
   */
  audioFile: string;
  /** Ordered array of transcript segments. */
  segments: Segment[];
  /** Vocabulary items shown in the collapsible summary panel. */
  vocab: VocabItem[];
  /** Optional Phase 4 alias for manually authored vocabulary summaries. */
  vocabSummary?: VocabItem[];
  /** Grammar notes shown in the collapsible summary panel. */
  grammar: GrammarItem[];
  /** Optional Phase 4 alias for manually authored grammar summaries. */
  grammarSummary?: GrammarItem[];
  /** ISO 8601 creation date, e.g. "2026-04-23". */
  createdAt: string;
  /** Optional Phase 3 alignment metadata. Missing for older Phase 2 lessons. */
  alignmentMeta?: {
    alignerRequested: string;
    alignerUsed: string;
    fallbackOccurred: boolean;
    hasTokenTimings: boolean;
    strictAlignment: boolean;
    externalAlignmentPath?: string;
    warnings: string[];
    notes: string[];
  };
}

/** Minimal lesson metadata used on the library page (subset of Lesson). */
export interface LessonMeta {
  id: string;
  title: string;
  description: string;
  level: Lesson['level'];
  durationSeconds: number;
}

/** Row in /lessons/index.json generated from processed lesson outputs. */
export interface LessonManifestEntry {
  id: string;
  title: string;
  source: string;
  language: string;
  tags: string[];
  audioSrc: string;
  lessonJsonSrc: string;
  captionsSrc: string;
  durationSec: number;
  segmentCount: number;
  description?: string;
  level?: Lesson['level'];
  alignerUsed?: string;
  createdAt?: string;
}
