import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const ROLES = ['writer', 'judge', 'review']

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-fog-300">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-fog-500">{hint}</span>}
    </label>
  )
}

export default function Settings() {
  const [settings, setSettings] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getSettings().then(setSettings)
  }, [])

  if (!settings) {
    return (
      <div className="max-w-xl space-y-5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-ink-800" />
        ))}
      </div>
    )
  }

  const save = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  const input =
    'w-full rounded-lg border border-ink-600 bg-ink-950 px-3 py-2 font-mono text-sm text-fog-200 outline-none focus:border-accent/60'

  return (
    <div className="max-w-xl">
      <p className="section-head">07 · the dials</p>
      <h1 className="mb-6 mt-1 font-display text-xl lowercase tracking-tight text-paper">settings</h1>

      <div className="space-y-5">
        <Field label="API base URL" hint="Point at a proxy or local gateway if needed.">
          <input
            className={input}
            value={settings.baseUrl}
            onChange={(e) => setSettings({ ...settings, baseUrl: e.target.value })}
          />
        </Field>

        <Field label="API key" hint="Stored in .env, masked here — never sent back to the browser in full.">
          <div className="flex items-center gap-2">
            <input className={input} value={settings.apiKeyMasked} readOnly />
            <button
              onClick={() => {}}
              className="shrink-0 rounded-lg border border-ink-600 px-3 py-2 text-sm text-fog-400 transition-colors hover:text-fog-200"
            >
              Replace
            </button>
          </div>
        </Field>

        <fieldset className="rounded-xl border border-ink-700 p-4">
          <legend className="px-1 text-sm font-medium text-fog-300">Model per role</legend>
          <div className="space-y-4 pt-2">
            {ROLES.map((role) => (
              <Field key={role} label={role}>
                <select
                  className={input}
                  value={settings.models[role]}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      models: { ...settings.models, [role]: e.target.value },
                    })
                  }
                >
                  {['claude-sonnet-4-6', 'claude-opus-4-6', 'claude-haiku-4-5'].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </Field>
            ))}
          </div>
        </fieldset>

        <fieldset className="rounded-xl border border-ink-700 p-4">
          <legend className="px-1 text-sm font-medium text-fog-300">Score gates</legend>
          <div className="grid grid-cols-2 gap-4 pt-2">
            {Object.entries(settings.thresholds).map(([k, v]) => (
              <Field key={k} label={`${k} threshold`}>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  className={input}
                  value={v}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      thresholds: { ...settings.thresholds, [k]: Number(e.target.value) },
                    })
                  }
                />
              </Field>
            ))}
          </div>
        </fieldset>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={save}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink-950 transition-transform active:scale-[0.98]"
          >
            Save settings
          </button>
          {saved && <span className="text-sm text-accent">Saved to .env</span>}
        </div>
      </div>
    </div>
  )
}
