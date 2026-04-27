import { useState } from 'react'
import type { VocabItem, GrammarItem } from '../types/lesson'

interface Props {
  vocab: VocabItem[]
  grammar: GrammarItem[]
}

/** Collapsible panel showing vocabulary and grammar notes for the lesson. */
export function VocabPanel({ vocab, grammar }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-t border-gray-100">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold
                   text-gray-600 hover:bg-gray-50 transition-colors"
        aria-expanded={open}
      >
        <span>Vocab &amp; Grammar</span>
        <svg
          className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4">
          {vocab.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Vocabulary
              </h3>
              <dl className="space-y-2">
                {vocab.map((item, i) => (
                  <div key={i}>
                    <dt className="inline font-medium text-gray-800">{item.word}</dt>
                    <dd className="inline text-gray-500 before:content-['_—_']">
                      {item.definition}
                    </dd>
                    {item.example && (
                      <p className="mt-0.5 text-xs text-gray-400 italic">{item.example}</p>
                    )}
                  </div>
                ))}
              </dl>
            </section>
          )}

          {grammar.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Grammar Notes
              </h3>
              <div className="space-y-3">
                {grammar.map((item, i) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-3">
                    <p className="font-medium text-gray-700 text-sm">{item.title}</p>
                    <p className="text-sm text-gray-500 mt-0.5">{item.explanation}</p>
                    {item.example && (
                      <p className="text-sm text-brand-700 italic mt-1">{item.example}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
