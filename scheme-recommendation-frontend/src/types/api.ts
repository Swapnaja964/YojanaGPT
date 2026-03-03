export interface UserProfile {
  user_id?: string
  state?: string
  district?: string
  pincode?: string
  age?: number
  gender?: 'male' | 'female' | 'other' | 'unspecified' | string
  category?: string
  income_annual?: number
  occupation?: string
  education_level?: string
  farmer?: boolean
  land_area?: number
  land_type?: string
  disability?: string
  business_type?: string
  enterprise_registered?: boolean
  enterprise_registration_number?: string
  enterprise_sector?: string
  established_date?: string
  effective_date?: string
  date_of_start?: string
  date_of_commencement?: string
  start_date?: string
  registered_with_bocwwb?: boolean
  registered_sanitation_worker_child?: boolean
  tourism_project_type?: string
  textile_unit_type?: string
  documents?: Record<string, string>
  extra_flags?: Record<string, unknown>
}

export interface SchemeScore {
  R: number
  S: number
  F: number
  final: number
}

export interface EligibilitySummary {
  required_matched: number
  required_total: number
  optional_matched: number
}

export interface Clause {
  field: string
  operator: string
  value: string | number
  status: 'matched' | 'failed' | 'optional'
}

export interface SchemeResult {
  scheme_id: string
  scheme_name: string
  description: string
  scores: SchemeScore
  eligibility_summary: EligibilitySummary
  clauses: Clause[]
}

export interface RankResponse {
  results: SchemeResult[]
}
