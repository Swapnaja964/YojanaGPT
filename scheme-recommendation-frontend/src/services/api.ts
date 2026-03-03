import axios from 'axios'
import type { UserProfile, RankResponse } from '@/types/api'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

export async function rankSchemes(profile: UserProfile): Promise<RankResponse> {
  try {
    const { data } = await api.post<RankResponse>('/rank', profile)
    if (!data || !Array.isArray(data.results)) throw new Error()
    return data
  } catch {
    throw new Error('Unable to fetch scheme recommendations.')
  }
}

export { api }
