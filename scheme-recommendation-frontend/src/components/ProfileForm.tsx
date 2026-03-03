import React, { useMemo, useState } from 'react'
import type { UserProfile } from '@/types/api'

type Props = {
  onSubmit: (profile: UserProfile) => Promise<void> | void
}

const STATES = [
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chhattisgarh',
  'Delhi',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
  'Jammu and Kashmir',
  'Ladakh'
]

const GENDERS = ['male', 'female', 'other', 'unspecified'] as const
const CATEGORIES = ['General', 'SC', 'ST', 'OBC'] as const

export default function ProfileForm({ onSubmit }: Props) {
  const [state, setState] = useState<UserProfile>({
    state: '',
    age: undefined,
    gender: undefined,
    category: undefined,
    disability: undefined,
    income_annual: undefined,
    occupation: '',
    land_area: undefined
  })
  const [hasDisability, setHasDisability] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = useMemo(() => !submitting, [submitting])

  function toNumberOrUndefined(v: string): number | undefined {
    if (v === '' || v === undefined || v === null) return undefined
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    try {
      const payload: UserProfile = {
        ...state,
        disability: hasDisability ? (state.disability || 'unspecified') : undefined
      }
      await onSubmit(payload)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <section className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-base font-semibold tracking-tight">Personal Details</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium">State</label>
            <select
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.state || ''}
              onChange={(e) => setState((s) => ({ ...s, state: e.target.value || '' }))}
            >
              <option value="">Select state</option>
              {STATES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Age</label>
            <input
              type="number"
              min={0}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.age ?? ''}
              onChange={(e) => setState((s) => ({ ...s, age: toNumberOrUndefined(e.target.value) }))}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Gender</label>
            <select
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.gender || ''}
              onChange={(e) =>
                setState((s) => ({ ...s, gender: (e.target.value || undefined) as UserProfile['gender'] }))
              }
            >
              <option value="">Select gender</option>
              {GENDERS.map((g) => (
                <option key={g} value={g}>
                  {g[0].toUpperCase() + g.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Category</label>
            <select
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.category || ''}
              onChange={(e) => setState((s) => ({ ...s, category: (e.target.value || undefined) as string }))}
            >
              <option value="">Select category</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium">Disability</label>
            <button
              type="button"
              onClick={() => {
                const next = !hasDisability
                setHasDisability(next)
                setState((s) => ({ ...s, disability: next ? (s.disability || 'unspecified') : undefined }))
              }}
              className={
                'inline-flex items-center rounded-md px-3 py-2 text-sm ' +
                (hasDisability
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200')
              }
            >
              {hasDisability ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-base font-semibold tracking-tight">Economic Details</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium">Income (annual, ₹)</label>
            <input
              type="number"
              min={0}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.income_annual ?? ''}
              onChange={(e) =>
                setState((s) => ({ ...s, income_annual: toNumberOrUndefined(e.target.value) }))
              }
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Occupation</label>
            <input
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.occupation || ''}
              onChange={(e) => setState((s) => ({ ...s, occupation: e.target.value }))}
              placeholder="e.g., Farmer"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Land Area (hectares)</label>
            <input
              type="number"
              min={0}
              step="0.01"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={state.land_area ?? ''}
              onChange={(e) => setState((s) => ({ ...s, land_area: toNumberOrUndefined(e.target.value) }))}
            />
          </div>
        </div>
      </section>

      <div className="flex items-center justify-end">
        <button
          type="submit"
          disabled={!canSubmit}
          className={
            'inline-flex items-center rounded-md px-4 py-2 text-sm font-medium ' +
            (submitting
              ? 'cursor-not-allowed bg-gray-300 text-gray-600'
              : 'bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500')
          }
        >
          {submitting ? 'Submitting...' : 'Submit'}
        </button>
      </div>
    </form>
  )
}
