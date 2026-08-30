import 'leaflet/dist/leaflet.css'

import { useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, ZoomControl } from 'react-leaflet'
import { Link } from 'react-router-dom'

import { PageHeader } from '@/components/AppShell'
import { SeverityChip } from '@/components/SeverityChip'
import { MODULE_LABEL, type ModuleCode } from '@/data/types'
import { DISTRICT } from '@/data/works'
import { rupeesShort } from '@/lib/format'
import { useReviews } from '@/lib/reviewStore'
import { SEVERITIES, SEVERITY_STYLE } from '@/lib/severity'
import { cn } from '@/lib/utils'

type View = 'ALL' | 'FLAGGED'

export function DistrictMap() {
  const { works } = useReviews()
  const [view, setView] = useState<View>('FLAGGED')
  const [module, setModule] = useState<ModuleCode | 'ALL'>('ALL')

  const visible = useMemo(
    () =>
      works
        .filter((w) => (view === 'FLAGGED' ? w.flags.length > 0 : true))
        .filter((w) => (module === 'ALL' ? true : w.flags.some((f) => f.module === module))),
    [works, view, module],
  )

  return (
    <div>
      <PageHeader
        eyebrow={`${DISTRICT.name} district · ${DISTRICT.state}`}
        title="District map"
        meta={`${visible.length} works plotted. Marker size follows severity; click one to open its findings.`}
      />

      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-5 py-2.5">
        <div className="flex rounded-[2px] border border-rule-strong">
          {(['FLAGGED', 'ALL'] as View[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={cn(
                'px-3 py-1 text-[12px] transition-colors',
                view === v ? 'bg-seal text-white' : 'bg-surface text-ink-muted hover:text-ink',
              )}
            >
              {v === 'FLAGGED' ? 'With findings' : 'All works'}
            </button>
          ))}
        </div>

        <select
          value={module}
          onChange={(e) => setModule(e.target.value as ModuleCode | 'ALL')}
          className="rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12px]"
        >
          <option value="ALL">All modules</option>
          {(Object.keys(MODULE_LABEL) as ModuleCode[]).map((m) => (
            <option key={m} value={m}>
              {MODULE_LABEL[m]}
            </option>
          ))}
        </select>

        <div className="ml-auto flex flex-wrap items-center gap-3">
          {SEVERITIES.map((tier) => (
            <span key={tier} className="flex items-center gap-1.5 text-[11px] text-ink-muted">
              <span
                aria-hidden
                className="inline-block rounded-full"
                style={{
                  width: markerRadius(tier) * 1.6,
                  height: markerRadius(tier) * 1.6,
                  backgroundColor: SEVERITY_STYLE[tier].hex,
                }}
              />
              {tier}
            </span>
          ))}
        </div>
      </div>

      <div className="h-[calc(100vh-190px)] min-h-[440px]">
        <MapContainer
          center={[DISTRICT.centroid.lat, DISTRICT.centroid.lon]}
          zoom={9}
          zoomControl={false}
          scrollWheelZoom
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ZoomControl position="bottomright" />

          {visible.map((w) => (
            <CircleMarker
              key={w.workId}
              center={[w.lat, w.lon]}
              radius={markerRadius(w.severity)}
              pathOptions={{
                color: '#ffffff',
                weight: 1.5,
                fillColor: SEVERITY_STYLE[w.severity].hex,
                fillOpacity: 0.9,
              }}
            >
              <Popup>
                <div className="min-w-[220px] font-sans">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[12px] font-medium">{w.workId}</span>
                    <SeverityChip severity={w.severity} size="sm" />
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-ink-muted">
                    {w.workType} · {w.block}
                  </div>
                  <div className="mt-1.5 font-mono text-[12px] tabular-nums">
                    {rupeesShort(w.estimatedCost)}
                  </div>
                  {w.flags[0] ? (
                    <p className="mt-2 text-[11.5px] leading-snug">{w.flags[0].explanation}</p>
                  ) : (
                    <p className="mt-2 text-[11.5px] text-ink-faint">No finding raised.</p>
                  )}
                  <Link
                    to={`/district/works/${w.workId}`}
                    className="mt-2 inline-block text-[12px] font-medium text-seal hover:underline"
                  >
                    Open work detail →
                  </Link>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}

/** Severity is carried by size as well as colour, so the map survives print and CVD. */
function markerRadius(severity: string): number {
  switch (severity) {
    case 'CRITICAL':
      return 10
    case 'HIGH':
      return 8
    case 'MEDIUM':
      return 6
    default:
      return 4
  }
}
