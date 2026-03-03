import React, { useState } from 'react'
import Layout from '../components/Layout'
import ProfileForm from '../components/ProfileForm'
import SchemeCard from '../components/SchemeCard'
import { rankSchemes } from '../services/api'
import type { RankResponse, UserProfile } from '@/types/api'

export default function Home() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<RankResponse | null>(null)

  async function handleSubmit(profile: UserProfile) {
    setLoading(true)
    setError(null)
    try {
      const res = await rankSchemes(profile)
      setResults(res)
      console.log('Rank results:', res)
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <ProfileForm onSubmit={handleSubmit} />

      <section className="mt-6">
        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="h-5 w-2/3 animate-pulse rounded bg-gray-200" />
                <div className="mt-3 h-6 w-24 animate-pulse rounded-full bg-gray-200" />
                <div className="mt-5 space-y-2">
                  <div className="h-2 w-full animate-pulse rounded bg-gray-200" />
                  <div className="h-2 w-4/5 animate-pulse rounded bg-gray-200" />
                  <div className="h-2 w-3/5 animate-pulse rounded bg-gray-200" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && results && (results.results?.length ?? 0) === 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 text-sm text-gray-600">
            No recommendations yet. Submit the form to see matching schemes.
          </div>
        )}

        {!loading && results && (results.results?.length ?? 0) > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...results.results]
              .sort((a, b) => (b.scores?.final ?? 0) - (a.scores?.final ?? 0))
              .map((scheme) => (
                <SchemeCard key={scheme.scheme_id} scheme={scheme} />
              ))}
          </div>
        )}
      </section>
    </Layout>
  )
}
