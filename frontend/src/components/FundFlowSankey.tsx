import { sankey, sankeyLinkHorizontal, type SankeyNode } from 'd3-sankey'
import { useMemo } from 'react'

import type { StateRow } from '@/api/types'
import { rupeesShort } from '@/lib/format'

/**
 * Where the money stops.
 *
 * A Sankey is the right form here because the question is not "how much" but
 * "how much made it to the next stage" — the width of a link *is* the answer,
 * and the narrowing between stages is the finding.
 *
 * Every figure is computed from the same state roll-up the table above uses.
 * Nothing here is illustrative.
 */

interface Node {
  name: string
  kind: 'flow' | 'stalled'
}
interface Link {
  source: number
  target: number
  value: number
}

const SEAL = '#16457e'
const STALLED = '#a9670c'

export function FundFlowSankey({ states, height = 260 }: { states: StateRow[]; height?: number }) {
  const totals = useMemo(() => {
    const sanctioned = states.reduce((n, s) => n + s.sanctioned_amount, 0)
    const disbursed = states.reduce((n, s) => n + s.disbursed_amount, 0)
    return { sanctioned, disbursed, undisbursed: Math.max(0, sanctioned - disbursed) }
  }, [states])

  const width = 720
  const layout = useMemo(() => {
    if (totals.sanctioned <= 0) return null

    const nodes: Node[] = [
      { name: 'Sanctioned', kind: 'flow' },
      { name: 'Released to agencies', kind: 'flow' },
      { name: 'Not yet released', kind: 'stalled' },
    ]
    const links: Link[] = [
      { source: 0, target: 1, value: totals.disbursed },
      { source: 0, target: 2, value: totals.undisbursed },
    ].filter((l) => l.value > 0)

    const generator = sankey<Node, Link>()
      .nodeWidth(14)
      .nodePadding(22)
      .extent([
        [1, 6],
        [width - 1, height - 6],
      ])

    return generator({
      nodes: nodes.map((d) => ({ ...d })),
      links: links.map((d) => ({ ...d })),
    })
  }, [totals, height])

  if (!layout) {
    return (
      <p className="text-[12px] text-ink-muted">
        No sanctioned value recorded yet, so there is no flow to draw.
      </p>
    )
  }

  const path = sankeyLinkHorizontal<Node, Link>()

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full min-w-[560px]"
        role="img"
        aria-label={`Of ${rupeesShort(totals.sanctioned)} sanctioned, ${rupeesShort(totals.disbursed)} has been released and ${rupeesShort(totals.undisbursed)} has not.`}
      >
        <g fill="none">
          {layout.links.map((link, i) => {
            const target = link.target as SankeyNode<Node, Link>
            return (
              <path
                key={i}
                d={path(link) ?? undefined}
                stroke={target.kind === 'stalled' ? STALLED : SEAL}
                strokeOpacity={0.28}
                strokeWidth={Math.max(1, link.width ?? 1)}
              />
            )
          })}
        </g>

        <g>
          {layout.nodes.map((node, i) => {
            const x0 = node.x0 ?? 0
            const x1 = node.x1 ?? 0
            const y0 = node.y0 ?? 0
            const y1 = node.y1 ?? 0
            const value = node.value ?? 0
            const share = (value / totals.sanctioned) * 100
            const onRight = x0 > width / 2
            return (
              <g key={i}>
                <rect
                  x={x0}
                  y={y0}
                  width={x1 - x0}
                  height={Math.max(1, y1 - y0)}
                  fill={node.kind === 'stalled' ? STALLED : SEAL}
                  rx={1}
                />
                <text
                  x={onRight ? x0 - 8 : x1 + 8}
                  y={(y0 + y1) / 2 - 6}
                  textAnchor={onRight ? 'end' : 'start'}
                  className="fill-ink"
                  style={{ fontSize: 12, fontWeight: 500 }}
                >
                  {node.name}
                </text>
                <text
                  x={onRight ? x0 - 8 : x1 + 8}
                  y={(y0 + y1) / 2 + 10}
                  textAnchor={onRight ? 'end' : 'start'}
                  className="fill-ink-muted"
                  style={{ fontSize: 11, fontVariantNumeric: 'tabular-nums' }}
                >
                  {rupeesShort(value)} · {share.toFixed(0)}%
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
