import 'leaflet/dist/leaflet.css'

import { CircleMarker, MapContainer, Popup, TileLayer, ZoomControl } from 'react-leaflet'

import type { StateRow } from '@/api/types'
import { rupeesShort } from '@/lib/format'

/**
 * Open critical findings by state, as a proportional-symbol map.
 *
 * Deliberately not a filled choropleth. Colouring a whole state by one figure
 * makes the eye read the largest state as the worst, which is a property of
 * geography rather than of the data. Area encodes the count instead, and every
 * marker carries its number so nothing depends on judging a circle by sight.
 */

const CENTROIDS: Record<string, [number, number]> = {
  Rajasthan: [26.5, 73.8],
  Kerala: [10.4, 76.3],
  'Madhya Pradesh': [23.3, 78.3],
  Maharashtra: [19.6, 75.7],
  'Tamil Nadu': [11.0, 78.6],
  'Uttar Pradesh': [27.0, 80.9],
  Karnataka: [15.3, 75.7],
  Gujarat: [22.6, 71.7],
  Bihar: [25.7, 85.4],
  'West Bengal': [23.4, 87.9],
}

const CRITICAL = '#ae1414'

export function NationalMap({ states }: { states: StateRow[] }) {
  const plotted = states.filter((s) => CENTROIDS[s.state])
  const maxCritical = Math.max(...plotted.map((s) => s.open_critical), 1)

  if (plotted.length === 0) {
    return (
      <p className="text-[12px] text-ink-muted">
        No centroid on file for the states in this dataset.
      </p>
    )
  }

  return (
    <div className="h-[380px] overflow-hidden rounded-[3px] border border-rule">
      <MapContainer
        center={[22.5, 79.0]}
        zoom={4}
        zoomControl={false}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ZoomControl position="bottomright" />

        {plotted.map((s) => {
          // Radius scaled by square root so area, not radius, tracks the count.
          const radius = 8 + Math.sqrt(s.open_critical / maxCritical) * 24
          return (
            <CircleMarker
              key={s.state}
              center={CENTROIDS[s.state]}
              radius={radius}
              pathOptions={{
                color: '#ffffff',
                weight: 1.5,
                fillColor: CRITICAL,
                fillOpacity: 0.55,
              }}
            >
              <Popup>
                <div className="min-w-[200px] font-sans">
                  <div className="text-[13px] font-medium">{s.state}</div>
                  <dl className="mt-1.5 space-y-0.5 text-[11.5px]">
                    <Row label="Works" value={s.works.toLocaleString('en-IN')} />
                    <Row label="Open critical" value={String(s.open_critical)} />
                    <Row label="Open high" value={String(s.open_high)} />
                    <Row label="Sanctioned" value={rupeesShort(s.sanctioned_amount)} />
                    <Row label="Utilisation" value={`${s.utilisation_pct.toFixed(1)}%`} />
                  </dl>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="font-mono tabular-nums">{value}</dd>
    </div>
  )
}
