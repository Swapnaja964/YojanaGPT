import React, { useState } from 'react'
import Layout from '../components/Layout'
import ProfileForm from '../components/ProfileForm'
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

      <div className="mt-6">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-indigo-600" />
            Loading recommendations...
          </div>
        )}
        {error && (
          <div className="mt-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    </Layout>
  )
}
