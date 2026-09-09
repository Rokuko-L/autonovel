import { useEffect, useState } from 'react'
import { useApp } from '../state.jsx'
import { api } from '../api/client.js'
import { navigate, projectRoute } from '../router.js'
import { PhaseBadge, ScoreSig, Button, EmptyState, Hint, Skel, timeAgo } from '../components/ui.jsx'

/**
 * Landing page: the shelf. Project cards surface each project's most
 * important signal (phase, latest score, word count) at a glance; the
 * creation wizard walks a new author from first visit to a launched run
 * in under a minute.
 */

const STEPS = ['identity', 'premise', 'shape', 'launch']

const SEG = {
  wrapper: 'flex border border-ink-600',
  btn: (active) =>
    `flex-1 px-3 py-1.5 font-mono text-xs transition-colors ${
      active ? 'bg-accent text-ink-950' : 'text-fog-400 hover:text-fog-200'
    }`,
}

function ProjectCard({ p }) {
  const progress = p.chaptersTotal ? Math.round((p.chaptersDone / p.chaptersTotal) * 100) : 0
  return (
    <button
      className="group w-full p-5 text-left transition-colors hover:bg-ink-850"
      onClick={() => {
        api.setActiveProject(p.name)
        navigate(projectRoute(p.name))
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-display text-base tracking-tight text-paper group-hover:text-accent">
            {p.title === 'Untitled' ? <span className="text-fog-400">{p.name}</span> : p.title}
          </p>
          <p className="mt-0.5 truncate font-mono text-[10px] text-fog-500">{p.name}</p>
        </div>
        <PhaseBadge phase={p.phase} running={p.running} />
      </div>

      {p.genre && <p className="mt-2 truncate font-prose text-xs italic text-fog-400">{p.genre}</p>}

      <div className="mt-4 flex items-center justify-between">
        <ScoreSig score={p.novelScore || p.foundationScore || null} label="unscored" />
        <span className="font-mono text-xs text-fog-400">
          {p.words ? `${(p.words / 1000).toFixed(1)}k words` : 'no prose yet'}
        </span>
      </div>

      {p.chaptersTotal > 0 && (
        <div className="mt-3">
          <div className="flex justify-between font-mono text-[10px] text-fog-500">
            <span>ch {p.chaptersDone}/{p.chaptersTotal}</span>
            <span>{progress}%</span>
          </div>
          <div className="mt-1 h-1 bg-ink-700">
            <div className="h-full bg-accent/70 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      <p className="mt-3 flex items-center justify-between font-mono text-[10px] text-fog-500">
        <span>upd {timeAgo(p.updatedAt)}</span>
        <span className="text-fog-500 transition-colors group-hover:text-accent">open ›</span>
      </p>
    </button>
  )
}

function Wizard({ onClose, onLaunch }) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    name: '', genre: '', notes: '', notesPath: '', notesMode: 'text',
    chapters: 24, chaptersCustom: false,
    wordsPerChapter: 3000, wordsCustom: false,
    revisionCycles: 3, perspective: 'third_person',
  })
  const [error, setError] = useState(null)
  const [launching, setLaunching] = useState(false)

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const stepValid = [
    form.name.trim() && form.genre.trim(),
    form.notesMode === 'path' ? form.notesPath.trim() : true,
    true, true,
  ][step]

  const launch = async () => {
    setLaunching(true)
    setError(null)
    try {
      await onLaunch(form)
    } catch (e) {
      setError(e.message)
      setLaunching(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg border border-ink-600 bg-ink-900" onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-line px-6 py-4">
          <div>
            <p className="section-head">initiate a novel</p>
            <p className="mt-0.5 font-mono text-[10px] text-fog-500">step {step + 1}/4 · {STEPS[step]}</p>
          </div>
          <button onClick={onClose} className="font-mono text-xs text-fog-500 hover:text-fog-200">✕</button>
        </header>

        <div className="flex gap-0.5 px-6 pt-4">
          {STEPS.map((s, i) => (
            <button key={s} onClick={() => i < step && setStep(i)} title={s}
              className={`h-1 flex-1 transition-colors ${i <= step ? 'bg-accent' : 'bg-ink-700'} ${i < step ? 'cursor-pointer' : ''}`} />
          ))}
        </div>

        <div className="space-y-4 px-6 py-5">
          {step === 0 && (
            <>
              <label className="block">
                <span className="field-label">project id — a short, unique folder name</span>
                <input className="field-input" placeholder="e.g. bells-second-son" value={form.name} onChange={set('name')} autoFocus />
              </label>
              <label className="block">
                <span className="field-label">genre classification <Hint>The genre steers the whole foundation pass — world, tone, and the story engine. Free text works best, e.g. "comedy fantasy misunderstanding".</Hint></span>
                <input className="field-input" placeholder="e.g. comedy fantasy misunderstanding" value={form.genre} onChange={set('genre')} />
              </label>
            </>
          )}

          {step === 1 && (
            <>
              <div className={SEG.wrapper}>
                {[['text', 'paste premise'], ['path', 'use a file']].map(([id, label]) => (
                  <button key={id} onClick={() => setForm({ ...form, notesMode: id })} className={SEG.btn(form.notesMode === id)}>
                    [{label}]
                  </button>
                ))}
              </div>
              {form.notesMode === 'text' ? (
                <label className="block">
                  <span className="field-label">premise / seed notes <Hint>Any rough premise — characters, situation, the joke of the world. Long notes are fine: they're summarized for the genre framework and kept in full as the seed.</Hint></span>
                  <textarea rows={7} className="field-input resize-none" placeholder="A stuck archivist discovers the royal library is quietly rewriting history…" value={form.notes} onChange={set('notes')} />
                </label>
              ) : (
                <label className="block">
                  <span className="field-label">path to an existing notes file</span>
                  <input className="field-input" placeholder="./notes/premise.txt" value={form.notesPath} onChange={set('notesPath')} />
                </label>
              )}
              <div>
                <span className="field-label">narration perspective</span>
                <div className={SEG.wrapper}>
                  {['third_person', 'first_person'].map((pv) => (
                    <button key={pv} onClick={() => setForm({ ...form, perspective: pv })} className={SEG.btn(form.perspective === pv)}>
                      {pv}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <span className="field-label">chapters</span>
                <div className={SEG.wrapper}>
                  {[12, 24, 30, 48].map((n) => (
                    <button key={n} onClick={() => setForm({ ...form, chapters: n, chaptersCustom: false })}
                      className={SEG.btn(form.chapters === n && !form.chaptersCustom)}>{n}</button>
                  ))}
                  <button onClick={() => setForm({ ...form, chaptersCustom: true })}
                    className={SEG.btn(form.chaptersCustom)}>custom</button>
                </div>
                {form.chaptersCustom && (
                  <input type="number" min={4} max={200} autoFocus
                    className="field-input mt-2 max-w-32" value={form.chapters}
                    onChange={(e) => setForm({ ...form, chapters: Math.max(4, Math.min(200, Number(e.target.value) || 0)) })} />
                )}
              </div>
              <div>
                <span className="field-label">words per chapter</span>
                <div className={SEG.wrapper}>
                  {[2000, 3000, 4000].map((n) => (
                    <button key={n} onClick={() => setForm({ ...form, wordsPerChapter: n, wordsCustom: false })}
                      className={SEG.btn(form.wordsPerChapter === n && !form.wordsCustom)}>{n}</button>
                  ))}
                  <button onClick={() => setForm({ ...form, wordsCustom: true })}
                    className={SEG.btn(form.wordsCustom)}>custom</button>
                </div>
                {form.wordsCustom && (
                  <input type="number" min={500} max={12000} step={100} autoFocus
                    className="field-input mt-2 max-w-32" value={form.wordsPerChapter}
                    onChange={(e) => setForm({ ...form, wordsPerChapter: Math.max(500, Math.min(12000, Number(e.target.value) || 0)) })} />
                )}
              </div>
              <div>
                <span className="field-label">revision cycles <Hint>After drafting, the pipeline re-reads the whole novel and adversarially edits it this many times. 3 is the sweet spot.</Hint></span>
                <div className={SEG.wrapper}>
                  {[1, 2, 3, 4].map((n) => (
                    <button key={n} onClick={() => setForm({ ...form, revisionCycles: n })} className={SEG.btn(form.revisionCycles === n)}>{n}</button>
                  ))}
                </div>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="space-y-2 border border-line bg-ink-950 p-4 font-mono text-xs leading-relaxed">
              {[['project', form.name], ['genre', form.genre],
                ['premise', form.notesMode === 'path' ? form.notesPath : `${form.notes.trim().split(/\s+/).filter(Boolean).length} words pasted`],
                ['perspective', form.perspective], ['chapters', `${form.chapters} × ${form.wordsPerChapter}w`],
                ['revision cycles', String(form.revisionCycles)]].map(([k, v]) => (
                <p key={k} className="flex justify-between gap-6">
                  <span className="text-fog-500">{k}</span>
                  <span className="truncate text-fog-200">{v}</span>
                </p>
              ))}
              <p className="border-t border-line pt-2 text-[10px] leading-relaxed text-fog-500">
                the run starts as a background process. foundation (world, characters, outline) takes about an hour —
                you can close this window and come back any time; the shelf remembers where everything stands.
              </p>
            </div>
          )}

          {error && <p className="border-l-2 border-bad bg-bad/5 px-3 py-2 font-mono text-[11px] leading-relaxed text-bad">{error}</p>}
        </div>

        <footer className="flex items-center justify-between border-t border-line px-6 py-4">
          <Button onClick={() => (step === 0 ? onClose() : setStep(step - 1))} disabled={launching}>
            {step === 0 ? 'cancel' : '‹ back'}
          </Button>
          {step < 3 ? (
            <Button variant="accent" disabled={!stepValid} onClick={() => setStep(step + 1)}>next ›</Button>
          ) : (
            <Button variant="solid" disabled={launching || !stepValid} onClick={launch}>
              {launching ? 'launching…' : 'launch run ▸'}
            </Button>
          )}
        </footer>
      </div>
    </div>
  )
}

export default function ProjectsGallery() {
  const { projects, launchProject } = useApp()
  const [wizard, setWizard] = useState(false)

  useEffect(() => {
    document.title = 'autonovel · projects'
  }, [])

  const doLaunch = async (form) => {
    await launchProject({
      name: form.name, genre: form.genre, notes: form.notes, notesPath: form.notesPath,
      chapters: form.chapters, wordsPerChapter: form.wordsPerChapter,
      revisionCycles: form.revisionCycles, perspective: form.perspective,
    })
    setWizard(false)
    navigate(projectRoute(form.name))
  }

  return (
    <main className="flex min-w-0 flex-1 overflow-y-auto">
      {/* my-auto centers short content but collapses to 0 when the grid
          outgrows the viewport, so the hero never scrolls out of reach */}
      <div className="mx-auto my-auto w-full max-w-6xl px-6 py-10">
        <header className="mb-10 text-center">
          <p className="section-head">your shelf</p>
          <h1 className="mt-2 font-display text-3xl font-bold lowercase tracking-tight text-paper">projects</h1>
          <p className="mx-auto mt-3 max-w-xl font-prose text-sm leading-relaxed text-fog-400">
            every novel is a project: one folder, one pipeline — foundation, drafting, revision, export.
            open one to watch it write itself, or start a fresh one.
          </p>
          <div className="mt-5">
            <Button variant="accent" onClick={() => setWizard(true)}>+ new project</Button>
          </div>
        </header>

        {!projects ? (
          <div className="dock grid grid-cols-1 gap-px sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => <Skel key={i} className="h-52" />)}
          </div>
        ) : projects.length === 0 ? (
          <EmptyState
            icon="✎"
            title="no projects yet"
            cta={<Button variant="accent" onClick={() => setWizard(true)}>+ start your first novel</Button>}
          >
            a project is a novel-in-progress. give the pipeline a genre and a rough premise, and it will build the
            world, outline the plot, draft every chapter, and revise itself — you supervise from the console.
          </EmptyState>
        ) : (
          <div className="dock grid grid-cols-1 gap-px sm:grid-cols-2 xl:grid-cols-3">
            {projects.map((p) => <ProjectCard key={p.name} p={p} />)}
          </div>
        )}
      </div>

      {wizard && <Wizard onClose={() => setWizard(false)} onLaunch={doLaunch} />}
    </main>
  )
}
