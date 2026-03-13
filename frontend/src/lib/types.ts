export type PageType = 'pricing' | 'changelog' | 'homepage' | 'jobs' | 'blog' | 'docs' | 'other'

export interface Monitor {
  id: string
  user_id: string
  name: string
  url: string
  competitor_name: string | null
  page_type: PageType
  check_interval_hours: number
  css_selector: string | null
  render_js: boolean
  use_firecrawl: boolean
  is_active: boolean
  next_check_at: string
  last_checked_at: string | null
  last_scrape_status: string
  last_scrape_error: string | null
  last_snapshot_id: string | null
  last_change_at: string | null
  consecutive_failures: number
  noise_patterns: string[]
  created_at: string
  updated_at: string
}

export interface Alert {
  id: string
  monitor_id: string
  diff_id: string
  analysis_id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'noise'
  category: string
  title: string
  summary: string
  is_acknowledged: boolean
  acknowledged_at: string | null
  notification_status: string
  created_at: string
  monitor?: Monitor
}

export interface Snapshot {
  _id: string
  monitor_id: string
  content_hash: string
  text_content: string
  raw_html_length: number
  fetched_at: string
  scraper_type: string
  status_code: number
}

export interface Diff {
  _id: string
  monitor_id: string
  snapshot_before_id: string
  snapshot_after_id: string
  unified_diff: string
  lines_added: number
  lines_removed: number
  hunks_count: number
  is_noise_only: boolean
  created_at: string
}

export interface Analysis {
  _id: string
  diff_id: string
  monitor_id: string
  severity: string
  category: string
  summary: string
  details: string
  confidence: number
  created_at: string
}

export interface NotificationSetting {
  id: string
  user_id: string
  channel: 'slack' | 'email'
  is_enabled: boolean
  min_severity: string
  slack_webhook_url: string | null
  email_address: string | null
  digest_mode: boolean
  digest_hour_utc: number | null
}

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'noise'

export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  critical: 'bg-rose-100 text-rose-700',
  high: 'bg-amber-100 text-amber-700',
  medium: 'bg-teal-100 text-teal-700',
  low: 'bg-blue-100 text-blue-700',
  noise: 'bg-gray-100 text-gray-500',
}

export const SEVERITY_DOT: Record<SeverityLevel, string> = {
  critical: 'bg-rose-500',
  high: 'bg-amber-500',
  medium: 'bg-teal-500',
  low: 'bg-blue-500',
  noise: 'bg-gray-400',
}
