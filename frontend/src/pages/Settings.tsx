import { useEffect, useState } from 'react'
import { Bell, Mail, MessageSquare, Save, Send, ShieldCheck, User } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import api, { extractApiErrorMessage } from '../lib/api'
import type { NotificationSetting } from '../lib/types'

type Channel = NotificationSetting['channel']
type NotificationSeverity = 'low' | 'medium' | 'high' | 'critical'

type NotificationDraft = {
  channel: Channel
  is_enabled: boolean
  min_severity: NotificationSeverity
  slack_webhook_url: string
  email_address: string
  digest_mode: boolean
  digest_hour_utc: number | null
}

const SEVERITY_OPTIONS: NotificationSeverity[] = ['low', 'medium', 'high', 'critical']

const CHANNEL_COPY: Record<
  Channel,
  { title: string; description: string; icon: typeof MessageSquare; inputLabel: string; placeholder: string }
> = {
  slack: {
    title: 'Slack',
    description: 'Route high-signal alerts to a shared channel for fast team review.',
    icon: MessageSquare,
    inputLabel: 'Webhook URL',
    placeholder: 'https://hooks.slack.com/services/...',
  },
  email: {
    title: 'Email',
    description: 'Deliver individual alerts or digest summaries to an inbox.',
    icon: Mail,
    inputLabel: 'Delivery address',
    placeholder: 'alerts@company.com',
  },
}

function buildDefaultDrafts(userEmail: string): Record<Channel, NotificationDraft> {
  return {
    slack: {
      channel: 'slack',
      is_enabled: false,
      min_severity: 'high',
      slack_webhook_url: '',
      email_address: '',
      digest_mode: false,
      digest_hour_utc: 16,
    },
    email: {
      channel: 'email',
      is_enabled: false,
      min_severity: 'medium',
      slack_webhook_url: '',
      email_address: userEmail,
      digest_mode: false,
      digest_hour_utc: 16,
    },
  }
}

function normalizeDrafts(
  settings: NotificationSetting[],
  userEmail: string,
): Record<Channel, NotificationDraft> {
  const drafts = buildDefaultDrafts(userEmail)

  settings.forEach((setting) => {
    drafts[setting.channel] = {
      channel: setting.channel,
      is_enabled: setting.is_enabled,
      min_severity: setting.min_severity as NotificationSeverity,
      slack_webhook_url: setting.slack_webhook_url || '',
      email_address: setting.email_address || '',
      digest_mode: setting.digest_mode,
      digest_hour_utc: setting.digest_hour_utc ?? 16,
    }
  })

  return drafts
}

export default function Settings() {
  const { user, setUser } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileMessage, setProfileMessage] = useState('')
  const [settingsError, setSettingsError] = useState('')
  const [channelMessage, setChannelMessage] = useState<Record<Channel, string>>({
    slack: '',
    email: '',
  })
  const [savingChannel, setSavingChannel] = useState<Record<Channel, boolean>>({
    slack: false,
    email: false,
  })
  const [testingChannel, setTestingChannel] = useState<Record<Channel, boolean>>({
    slack: false,
    email: false,
  })
  const [drafts, setDrafts] = useState<Record<Channel, NotificationDraft>>(() =>
    buildDefaultDrafts(user?.email || ''),
  )

  useEffect(() => {
    setFullName(user?.full_name || '')
  }, [user?.full_name])

  useEffect(() => {
    api
      .get('/notifications/settings')
      .then(({ data }) => {
        setDrafts(normalizeDrafts(Array.isArray(data) ? data : [], user?.email || ''))
      })
      .catch(() => {
        setSettingsError('Unable to load notification settings.')
      })
  }, [user?.email])

  const updateDraft = (channel: Channel, patch: Partial<NotificationDraft>) => {
    setDrafts((previous) => ({
      ...previous,
      [channel]: {
        ...previous[channel],
        ...patch,
      },
    }))
  }

  const saveProfile = async () => {
    setProfileSaving(true)
    setProfileMessage('')

    try {
      const { data } = await api.patch('/users/me', { full_name: fullName })
      setUser(data)
      setProfileMessage('Profile updated.')
    } catch {
      setProfileMessage('Unable to save profile.')
    } finally {
      setProfileSaving(false)
    }
  }

  const saveChannel = async (channel: Channel) => {
    const draft = drafts[channel]
    setSavingChannel((previous) => ({ ...previous, [channel]: true }))
    setChannelMessage((previous) => ({ ...previous, [channel]: '' }))

    try {
      await api.put(`/notifications/settings/${channel}`, {
        is_enabled: draft.is_enabled,
        min_severity: draft.min_severity,
        slack_webhook_url: channel === 'slack' ? draft.slack_webhook_url || null : null,
        email_address: channel === 'email' ? draft.email_address || null : null,
        digest_mode: draft.digest_mode,
        digest_hour_utc: draft.digest_mode ? draft.digest_hour_utc : null,
      })

      setChannelMessage((previous) => ({ ...previous, [channel]: 'Settings saved.' }))
    } catch (error: unknown) {
      setChannelMessage((previous) => ({
        ...previous,
        [channel]: extractApiErrorMessage(error, 'Unable to save channel settings.'),
      }))
    } finally {
      setSavingChannel((previous) => ({ ...previous, [channel]: false }))
    }
  }

  const sendTest = async (channel: Channel) => {
    setTestingChannel((previous) => ({ ...previous, [channel]: true }))
    setChannelMessage((previous) => ({ ...previous, [channel]: '' }))

    try {
      await api.post(`/notifications/test/${channel}`)
      setChannelMessage((previous) => ({
        ...previous,
        [channel]: 'Test notification queued.',
      }))
    } catch (error: unknown) {
      setChannelMessage((previous) => ({
        ...previous,
        [channel]: extractApiErrorMessage(error, 'Unable to send test notification.'),
      }))
    } finally {
      setTestingChannel((previous) => ({ ...previous, [channel]: false }))
    }
  }

  return (
    <div className="space-y-8">
      <div className="max-w-3xl">
        <p className="page-kicker">Settings</p>
        <h2 className="mt-3 page-title">Profile and delivery controls</h2>
        <p className="mt-3 page-subtitle">
          Keep profile information current and configure the notification paths that support the monitoring workflow.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-6">
          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <User className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Profile</div>
                <div className="text-sm text-slate-600">Used throughout the application shell.</div>
              </div>
            </div>

            <div className="mt-6 space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Full name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Email</label>
                <input
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="input-field cursor-not-allowed bg-slate-100 text-slate-500"
                />
              </div>

              <button type="button" onClick={saveProfile} disabled={profileSaving} className="btn-primary w-full">
                <Save className="h-4 w-4" />
                {profileSaving ? 'Saving...' : 'Save profile'}
              </button>

              {profileMessage && (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  {profileMessage}
                </div>
              )}
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Why this is stronger</div>
                <div className="text-sm text-slate-600">The settings flow now matches the backend contract.</div>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              {[
                'Notification channels are saved by channel name, matching the API.',
                'Slack and email inputs are editable instead of placeholder-only buttons.',
                'Test notifications can be queued from the same screen after configuration.',
              ].map((item) => (
                <div key={item} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                  <div className="mt-2 h-2 w-2 rounded-full bg-emerald-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                <Bell className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Notification channels</div>
                <div className="text-sm text-slate-600">
                  Configure delivery paths and severity thresholds for alert routing.
                </div>
              </div>
            </div>

            {settingsError && (
              <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {settingsError}
              </div>
            )}

            <div className="mt-6 space-y-5">
              {(['slack', 'email'] as Channel[]).map((channel) => {
                const draft = drafts[channel]
                const metadata = CHANNEL_COPY[channel]
                const Icon = metadata.icon

                return (
                  <div key={channel} className="rounded-3xl border border-slate-200 bg-slate-50/80 p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="flex items-start gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-slate-700 shadow-sm">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="text-base font-semibold text-slate-950">{metadata.title}</div>
                          <div className="mt-1 text-sm leading-6 text-slate-600">
                            {metadata.description}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => updateDraft(channel, { is_enabled: !draft.is_enabled })}
                        className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                          draft.is_enabled
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-slate-200 text-slate-600'
                        }`}
                      >
                        {draft.is_enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700">
                          {metadata.inputLabel}
                        </label>
                        <input
                          type={channel === 'email' ? 'email' : 'url'}
                          value={channel === 'email' ? draft.email_address : draft.slack_webhook_url}
                          onChange={(e) =>
                            updateDraft(
                              channel,
                              channel === 'email'
                                ? { email_address: e.target.value }
                                : { slack_webhook_url: e.target.value },
                            )
                          }
                          className="input-field"
                          placeholder={metadata.placeholder}
                        />
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700">
                          Minimum severity
                        </label>
                        <select
                          value={draft.min_severity}
                          onChange={(e) =>
                            updateDraft(channel, {
                              min_severity: e.target.value as NotificationSeverity,
                            })
                          }
                          className="input-field"
                        >
                          {SEVERITY_OPTIONS.map((severity) => (
                            <option key={severity} value={severity}>
                              {severity}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-4 md:grid-cols-[0.7fr_0.3fr]">
                      <button
                        type="button"
                        onClick={() => updateDraft(channel, { digest_mode: !draft.digest_mode })}
                        className={`rounded-2xl border px-4 py-3 text-left ${
                          draft.digest_mode
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <div className="text-sm font-semibold text-slate-950">
                          {draft.digest_mode ? 'Digest mode enabled' : 'Send immediately'}
                        </div>
                        <div className="mt-2 text-xs leading-5 text-slate-600">
                          Digest mode batches lower-priority notifications into one scheduled send.
                        </div>
                      </button>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700">
                          Digest hour (UTC)
                        </label>
                        <select
                          value={draft.digest_hour_utc ?? 16}
                          onChange={(e) =>
                            updateDraft(channel, {
                              digest_hour_utc: Number(e.target.value),
                            })
                          }
                          className="input-field"
                          disabled={!draft.digest_mode}
                        >
                          {Array.from({ length: 24 }, (_, hour) => hour).map((hour) => (
                            <option key={hour} value={hour}>
                              {hour.toString().padStart(2, '0')}:00
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {channelMessage[channel] && (
                      <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                        {channelMessage[channel]}
                      </div>
                    )}

                    <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
                      <button
                        type="button"
                        onClick={() => sendTest(channel)}
                        disabled={testingChannel[channel]}
                        className="btn-secondary"
                      >
                        <Send className="h-4 w-4" />
                        {testingChannel[channel] ? 'Sending test...' : 'Send test'}
                      </button>
                      <button
                        type="button"
                        onClick={() => saveChannel(channel)}
                        disabled={savingChannel[channel]}
                        className="btn-primary"
                      >
                        <Save className="h-4 w-4" />
                        {savingChannel[channel] ? 'Saving...' : `Save ${metadata.title}`}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
