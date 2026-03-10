import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import api from '../lib/api'
import type { NotificationSetting } from '../lib/types'
import { Bell, Mail, MessageSquare, Save, User } from 'lucide-react'

export default function Settings() {
  const { user } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [email] = useState(user?.email || '')
  const [notifications, setNotifications] = useState<NotificationSetting[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.get('/notifications/settings').then(({ data }) => {
      setNotifications(Array.isArray(data) ? data : [])
    }).catch(() => {})
  }, [])

  const saveProfile = async () => {
    setSaving(true)
    try {
      await api.patch('/users/me', { full_name: fullName })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { /* ignore */ }
    setSaving(false)
  }

  const toggleNotification = async (id: string, enabled: boolean) => {
    try {
      await api.patch(`/notifications/settings/${id}`, { is_enabled: !enabled })
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_enabled: !enabled } : n))
      )
    } catch { /* ignore */ }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>

      {/* Profile */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-teal-50 flex items-center justify-center">
            <User className="w-4.5 h-4.5 text-teal-700" />
          </div>
          <h2 className="text-sm font-semibold text-gray-900">Profile</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-[#FAFAF8] text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              disabled
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-400 cursor-not-allowed"
            />
          </div>
          <button
            onClick={saveProfile}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-full text-sm font-semibold hover:bg-gray-800 transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-amber-50 flex items-center justify-center">
            <Bell className="w-4.5 h-4.5 text-amber-700" />
          </div>
          <h2 className="text-sm font-semibold text-gray-900">Notification Channels</h2>
        </div>

        {notifications.length === 0 ? (
          <div className="space-y-3">
            {/* Default channels when no settings exist */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-[#FAFAF8] border border-gray-100">
              <div className="flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm font-medium text-gray-900">Slack</div>
                  <div className="text-xs text-gray-400">Not configured</div>
                </div>
              </div>
              <button className="px-3 py-1.5 rounded-xl text-xs font-medium text-teal-600 hover:bg-teal-50 transition border border-teal-200">
                Configure
              </button>
            </div>
            <div className="flex items-center justify-between p-4 rounded-xl bg-[#FAFAF8] border border-gray-100">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm font-medium text-gray-900">Email</div>
                  <div className="text-xs text-gray-400">Not configured</div>
                </div>
              </div>
              <button className="px-3 py-1.5 rounded-xl text-xs font-medium text-teal-600 hover:bg-teal-50 transition border border-teal-200">
                Configure
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((n) => (
              <div
                key={n.id}
                className="flex items-center justify-between p-4 rounded-xl bg-[#FAFAF8] border border-gray-100"
              >
                <div className="flex items-center gap-3">
                  {n.channel === 'slack' ? (
                    <MessageSquare className="w-5 h-5 text-gray-400" />
                  ) : (
                    <Mail className="w-5 h-5 text-gray-400" />
                  )}
                  <div>
                    <div className="text-sm font-medium text-gray-900 capitalize">{n.channel}</div>
                    <div className="text-xs text-gray-400">
                      Min severity: {n.min_severity} &middot; {n.digest_mode ? 'Digest mode' : 'Instant'}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => toggleNotification(n.id, n.is_enabled)}
                  className={`relative w-11 h-6 rounded-full transition ${n.is_enabled ? 'bg-teal-500' : 'bg-gray-200'}`}
                >
                  <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${n.is_enabled ? 'translate-x-5.5' : 'translate-x-0.5'}`} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
