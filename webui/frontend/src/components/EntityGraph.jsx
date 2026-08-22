import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'

cytoscape.use(fcose)

const KIND_COLOR = {
  character: '#ff6a3d',
  location: '#bab49e',
  faction: '#7a7568',
}

/**
 * Force-directed entity graph (cytoscape). Pan/zoom/hover built in;
 * tapping or hovering a node lights its edges + neighbours and shows
 * relationship labels. Data shape: contract.js entities {nodes, edges}.
 */
export default function EntityGraph({ nodes, edges }) {
  const ref = useRef(null)
  const cyRef = useRef(null)

  useEffect(() => {
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...nodes.map((n) => ({
          data: { id: n.id, label: n.label, kind: n.kind, status: n.status },
        })),
        ...edges.map((e, i) => ({
          data: { id: `e${i}`, source: e.from, target: e.to, label: e.label },
        })),
      ],
      layout: {
        name: 'fcose',
        animate: true,
        padding: 80,
        nodeSeparation: 240,
        idealEdgeLength: 220,
        nodeRepulsion: 24000,
        gravity: 0.2,
      },
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': '#14140f',
            'border-color': (el) => KIND_COLOR[el.data('kind')] ?? '#36342b',
            'border-width': 2,
            color: '#ddd7c3',
            'font-family': 'ui-monospace, monospace',
            'font-size': 7,
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: 16,
            height: 16,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#26251f',
            'curve-style': 'bezier',
            opacity: 0.9,
          },
        },
        {
          selector: 'edge.lit',
          style: {
            label: 'data(label)',
            'line-color': '#ff6a3d',
            width: 2.5,
            color: '#ff6a3d',
            'font-size': 6,
            'font-family': 'ui-monospace, monospace',
            'text-background-color': '#0a0a08',
            'text-background-opacity': 1,
            'text-background-padding': 1,
            'text-rotation': 'autorotate',
          },
        },
        {
          selector: 'node.dead',
          style: { 'border-style': 'dashed', color: '#e05252' },
        },
        {
          selector: '.dimmed',
          style: { opacity: 0.12 },
        },
      ],
      wheelSensitivity: 0.2,
    })

    // dead/doomed characters get dashed rings via status text
    cy.nodes().forEach((n) => {
      const s = (n.data('status') ?? '').toLowerCase()
      if (s.includes('dead') || s.includes('unknown')) n.addClass('dead')
    })

    const focus = (evt) => {
      const node = evt.target
      const nbhd = node.closedNeighborhood()
      cy.elements().addClass('dimmed')
      nbhd.removeClass('dimmed')
      nbhd.edges().addClass('lit')
    }
    const unfocus = () => {
      cy.elements().removeClass('dimmed')
      cy.edges().removeClass('lit')
    }
    cy.on('layoutstop', () => cy.fit(undefined, 60))
    cy.on('mouseover', 'node', focus)
    cy.on('mouseout', 'node', unfocus)

    cyRef.current = cy
    return () => cy.destroy()
  }, [nodes, edges])

  return (
    <div className="relative overflow-hidden rounded-xl border border-ink-700 bg-ink-950">
      <div ref={ref} className="h-[480px] w-full" />
      <p className="pointer-events-none absolute bottom-3 right-4 font-mono text-[10px] text-fog-500">
        hover to trace · scroll to zoom · drag to rearrange
      </p>
    </div>
  )
}
