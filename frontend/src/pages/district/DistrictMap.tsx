import 'leaflet/dist/leaflet.css'

import { useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, ZoomControl } from 'react-leaflet'
import { Link } from 'react-router-dom'

import { useDistrictMap, useDistrictRefs } from '@/api/hooks'
import type { Severity } from '@/api/types'
import {
  ErrorState,
  Loading,
  PageHeader,
  SeverityChip,
  SEVERITY_HEX,
  SEVERITY_ORDER,
} from '@/components/ui-kit'
import { rupeesShort } from '@/lib/format'
import { useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

/** Severity is carried by radius as well as colour, so the map survives print and CVD. */
function radiusFor(tier: Severity | null): number {
  switch (tier) {
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

export function DistrictMap() {
  const { me } = useSession()
  const districtId = me?.scope_district_id ?? undefined
  const [onlyFindings, setOnlyFindings] = useState(true)

  const refs = useDistrictRefs()
  const geo = useDistrictMap(districtId, onlyFindings)
  const district = refs.data?.find((d) => d.district_id === districtId)

  return (
    <div>
      <PageHeader
        eyebrow={district ? `${district.name} district · ${district.state}` : ' '}
        title="District map"
        meta={
          geo.data
            ? `${geo.data.features.length} works plotted. Marker size follows severity; click one to open its findings.`
            : 'Loading works…'
        }
      />

      <div className="flex flex-wrap items-center gap-3 border-b border-rule bg-surface px-5 py-2.5">
        <div className="flex rounded-[2px] border border-rule-strong">
          {[true, false].map((v) => (
            <button
              key={String(v)}
              type="button"
              onClick={() => setOnlyFindings(v)}
              className={cn(
                'px-3 py-1 text-[12px] transition-colors',
                onlyFindings === v ? 'bg-seal text-white' : 'bg-surface text-ink-muted hover:text-ink',
              )}
            >
              {v ? 'With findings' : 'All works'}
            </button>
          ))}
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-3">
          {SEVERITY_ORDER.map((tier) => (
            <span key={tier} className="flex items-center gap-1.5 text-[11px] text-ink-muted">
              <span
                aria-hidden
                className="inline-block rounded-full"
                style={{
                  width: radiusFor(tier) * 1.5,
                  height: radiusFor(tier) * 1.5,
                  backgroundColor: SEVERITY_HEX[tier],
                }}
              />
              {tier}
            </span>
          ))}
        </div>
      </div>

      {geo.isPending && <Loading rows={6} label="Loading map data" />}
      {geo.isError && <ErrorState message={(geo.error as Error).message} onRetry={() => geo.refetch()} />}

      {geo.data && district && (
        <div className="h-[calc(100vh-230px)] min-h-[420px]">
          <MapContainer
            center={[district.centroid_lat, district.centroid_lon]}
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

            {geo.data.features.map((f) => {
              const tier = f.properties.severity_tier
              return (
                <CircleMarker
                  key={f.properties.work_id}
                  center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
                  radius={radiusFor(tier)}
                  pathOptions={{
                    color: '#ffffff',
                    weight: 1.5,
                    fillColor: tier ? SEVERITY_HEX[tier] : '#9aa4ad',
                    fillOpacity: 0.9,
                  }}
                >
                  <Popup>
                    <div className="min-w-[220px] font-sans">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[12px] font-medium">
                          {f.properties.work_id}
                        </span>
                        <SeverityChip severity={tier} size="sm" />
                      </div>
                      <div className="mt-1 font-mono text-[11px] text-ink-muted">
                        {f.properties.work_type} · {f.properties.block}
                      </div>
                      <div className="mt-1.5 font-mono text-[12px] tabular-nums">
                        {rupeesShort(f.properties.estimated_cost)}
                      </div>
                      {f.properties.primary_finding ? (
                        <p className="mt-2 text-[11.5px] leading-snug">
                          {f.properties.primary_finding}
                        </p>
                      ) : (
                        <p className="mt-2 text-[11.5px] text-ink-faint">No finding raised.</p>
                      )}
                      <Link
                        to={`/district/works/${f.properties.work_id}`}
                        className="mt-2 inline-block text-[12px] font-medium text-seal hover:underline"
                      >
                        Open work detail →
                      </Link>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}
          </MapContainer>
        </div>
      )}
    </div>
  )
}
