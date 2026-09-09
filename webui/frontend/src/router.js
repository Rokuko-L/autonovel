import { useEffect, useState } from 'react'

/**
 * Tiny hash router. Routes:
 *   #/projects                      → landing gallery
 *   #/p/{project}                   → project overview
 *   #/p/{project}/pipeline/{tab}    → unified pipeline dashboard
 *   #/p/{project}/foundation/{tab}  → world bible / graph / characters…
 *   #/p/{project}/manuscript        → prose reader
 *   #/p/{project}/revision          → briefs & adversarial cuts
 *   #/p/{project}/ledger            → beats & harvests (contextual tool)
 *   #/p/{project}/arena             → chapter arena (contextual tool)
 *   #/settings                      → global configuration
 */

export function parseRoute(hash) {
  const segs = (hash || '#/projects').replace(/^#\/?/, '').split('/').filter(Boolean)
  if (segs[0] === 'p' && segs[1]) {
    return { name: 'project', project: decodeURIComponent(segs[1]), view: segs[2] || 'overview', tab: segs[3] || null }
  }
  if (segs[0] === 'settings') return { name: 'settings' }
  return { name: 'projects' }
}

export function href(route) {
  return `#${route}`
}

export function navigate(route) {
  window.location.hash = route
}

export function projectRoute(project, view = 'overview', tab = null) {
  return `/p/${encodeURIComponent(project)}${view && view !== 'overview' ? `/${view}` : ''}${tab ? `/${tab}` : ''}`
}

export function useRoute() {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}
