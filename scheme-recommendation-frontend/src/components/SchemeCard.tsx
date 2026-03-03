import React, { useMemo } from 'react'
import type { SchemeResult } from '../types/api'

type Props = {
  scheme: SchemeResult
}

function clamp01(n: number) {
  if (Number.isNaN(n)) return 0
  return Math.max(0, Math.min(1, n))
}

function Progress({ value, label }: { value: number; label: string }) {
  const pct = Math.round(clamp01(value) * 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded bg-gray-200">
        <div
          className="h-full rounded bg-indigo-600"
          style={{ width: `${pct}%` }}
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  )
}

export default function SchemeCard({ scheme }: Props) {
  const { scheme_name, scores, eligibility_summary } = scheme
  const finalPct = Math.round(clamp01(scores.final) * 100)

  const eligibilityLabel = useMemo(() => {
    const reqMatched = eligibility_summary.required_matched ?? 0
    const reqTotal = eligibility_summary.required_total ?? 0
    if (reqTotal > 0 && reqMatched === reqTotal) return 'Fully Eligible'
    if (reqMatched > 0) return 'Partially Eligible'
    return 'Not Eligible'
  }, [eligibility_summary])

  const eligibilityClass = useMemo(() => {
    switch (eligibilityLabel) {
      case 'Fully Eligible':
        return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
      case 'Partially Eligible':
        return 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
      default:
        return 'bg-rose-50 text-rose-700 ring-1 ring-rose-200'
    }
  }, [eligibilityLabel])

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold tracking-tight text-gray-900">{scheme_name}</h3>
          <div className={`mt-2 inline-flex items-center rounded px-2.5 py-1 text-xs ${eligibilityClass}`}>
            {eligibilityLabel}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-wider text-gray-500">Final Score</div>
          <div className="mt-1 inline-flex items-center rounded-full bg-indigo-600 px-3 py-1 text-white">
            <span className="text-lg font-semibold">{finalPct}</span>
            <span className="ml-1 text-xs">%</span>
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        <Progress value={scores.R} label="R (Rules)" />
        <Progress value={scores.S} label="S (Semantic)" />
        <Progress value={scores.F} label="F (Freshness Penalty)" />
      </div>
    </div>
  )
}
