import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup, Polyline, Rectangle, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import type { VesselTrack } from '../hooks/useAISStream';
import 'leaflet/dist/leaflet.css';

// Fix leaflet icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

interface MapViewerProps {
  vessels: Record<string, VesselTrack>;
  slicks: any[];
  layers: { liveAis: boolean, globalSlicks: boolean, eezGeofence: boolean, incoisVectors: boolean };
  incoisData: any[];
  selectedIncident: any;
  geofenceBbox: string;
  setGeofenceBbox: (bbox: string) => void;
  isDrawingZone?: boolean;
  setIsDrawingZone?: (v: boolean) => void;
}

const MUMBAI_EEZ = [
  [18.60, 71.95],
  [19.30, 71.95],
  [19.30, 72.68],
  [18.60, 72.68]
];

function MapController({ selectedIncident }: { selectedIncident: any }) {
  const map = useMap();
  useEffect(() => {
    if (selectedIncident && selectedIncident.coordinates) {
      map.flyTo([selectedIncident.coordinates.lat, selectedIncident.coordinates.lon], 10, { duration: 1.5 });
    }
  }, [selectedIncident, map]);

  useEffect(() => {
    const handleFly = (e: any) => {
      const bbox = e.detail;
      if (bbox) {
        try {
          const [minLon, minLat, maxLon, maxLat] = bbox.split(',').map(Number);
          if (!isNaN(minLon) && !isNaN(minLat) && !isNaN(maxLon) && !isNaN(maxLat)) {
            map.flyToBounds([[minLat, minLon], [maxLat, maxLon]], { duration: 1.5 });
          }
        } catch (err) {
          console.error('Invalid geofence bbox', err);
        }
      }
    };
    window.addEventListener('fly-to-bbox', handleFly);
    return () => window.removeEventListener('fly-to-bbox', handleFly);
  }, [map]);

  useEffect(() => {
    const handleObserve = () => {
      const bounds = map.getBounds();
      const minLat = bounds.getSouth().toFixed(4);
      const maxLat = bounds.getNorth().toFixed(4);
      const minLon = bounds.getWest().toFixed(4);
      const maxLon = bounds.getEast().toFixed(4);
      const boundsStr = `${minLon},${minLat},${maxLon},${maxLat}`;
      window.dispatchEvent(new CustomEvent('current-view-observed', { detail: boundsStr }));
    };
    window.addEventListener('observe-current-view', handleObserve);
    return () => window.removeEventListener('observe-current-view', handleObserve);
  }, [map]);

  return null;
}

function ZoneDrawer({ isDrawingZone, onZoneDrawn, geofenceBbox }: { isDrawingZone: boolean; onZoneDrawn: (bbox: string) => void; geofenceBbox: string }) {
  const [startPoint, setStartPoint] = useState<L.LatLng | null>(null);
  const [currentPoint, setCurrentPoint] = useState<L.LatLng | null>(null);
  const map = useMap();

  useMapEvents({
    click(e) {
      if (!isDrawingZone) return;
      if (!startPoint) {
        setStartPoint(e.latlng);
        setCurrentPoint(e.latlng);
        map.dragging.disable();
      } else {
        const minLat = Math.min(startPoint.lat, e.latlng.lat).toFixed(4);
        const maxLat = Math.max(startPoint.lat, e.latlng.lat).toFixed(4);
        const minLon = Math.min(startPoint.lng, e.latlng.lng).toFixed(4);
        const maxLon = Math.max(startPoint.lng, e.latlng.lng).toFixed(4);
        onZoneDrawn(`${minLon},${minLat},${maxLon},${maxLat}`);
        setStartPoint(null);
        setCurrentPoint(null);
        map.dragging.enable();
      }
    },
    mousemove(e) {
      if (isDrawingZone && startPoint) {
        setCurrentPoint(e.latlng);
      }
    }
  });

  if (startPoint && currentPoint) {
    const bounds = [[startPoint.lat, startPoint.lng], [currentPoint.lat, currentPoint.lng]];
    return <Rectangle bounds={bounds as any} pathOptions={{ color: '#0056b3', weight: 2, fillOpacity: 0.1, dashArray: '5, 5' }} />;
  }

  if (!startPoint && geofenceBbox) {
    const parts = geofenceBbox.split(',').map(Number);
    if (parts.length === 4 && parts.every(p => !isNaN(p))) {
        const [minLon, minLat, maxLon, maxLat] = parts;
        const bounds = [[minLat, minLon], [maxLat, maxLon]];
        return <Rectangle bounds={bounds as any} pathOptions={{ color: '#0056b3', weight: 2, fillOpacity: 0.1 }} />;
    }
  }

  return null;
}

export default function MapViewer({ vessels, layers, slicks, incoisData, selectedIncident, geofenceBbox, setGeofenceBbox, isDrawingZone, setIsDrawingZone }: MapViewerProps) {
  
  // Data is pre-filtered by App.tsx, just extract values

  // Data is pre-filtered by App.tsx, just extract values
  const visibleVessels = Object.values(vessels);
  const visibleSlicks = slicks;
  const visibleVectors = incoisData;

  return (
    <div className="map-layer">
      <MapContainer center={[18.9, 72.8]} zoom={9} style={{ height: '100%', width: '100%' }} zoomControl={false} preferCanvas={true}>
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
        />
        <MapController selectedIncident={selectedIncident} />
        <ZoneDrawer 
          isDrawingZone={isDrawingZone || false} 
          geofenceBbox={geofenceBbox}
          onZoneDrawn={(bbox) => { setGeofenceBbox(bbox); setIsDrawingZone?.(false); }} 
        />

        {layers.eezGeofence && (
          <Polygon 
            positions={MUMBAI_EEZ as any} 
            pathOptions={{ color: '#EF4444', weight: 2, dashArray: '6, 6', fillColor: '#EF4444', fillOpacity: 0.08 }} 
          />
        )}

        {layers.incoisVectors && visibleVectors.map((d, i) => {
          // Draw simple arrows for vectors
          const endLat = d.lat + (d.v * 0.01);
          const endLon = d.lon + (d.u * 0.01);
          return (
            <Polyline key={`vector-${i}`} positions={[[d.lat, d.lon], [endLat, endLon]]} pathOptions={{ color: '#0056b3', weight: 1, dashArray: '2, 4' }} />
          );
        })}

        {layers.liveAis && visibleVessels.map((v) => {
          let color = '#0056b3'; // blue nominal
          if (v.threat_score && v.threat_score >= 40 && v.threat_score < 75) color = '#F59E0B'; // amber
          if (v.threat_score && v.threat_score >= 75) color = '#EF4444'; // red

          const isEEZBreach = v.in_eez && v.threat_score && v.threat_score >= 50;
          if (isEEZBreach) color = '#EF4444'; // red if breached

          // Pulsing animation style inline using box-shadow
          const pulseShadow = isEEZBreach ? '0 0 10px 5px rgba(239,68,68,0.8)' : (v.threat_score && v.threat_score >= 75 ? '0 0 10px 5px rgba(239,68,68,0.5)' : 'none');
          
          const iconHtml = `<svg width="24" height="24" viewBox="0 0 24 24" style="transform: rotate(${v.heading}deg); overflow: visible;"><path d="M12 2L20 20L12 17L4 20L12 2Z" fill="${color}" stroke="white" stroke-width="1.5"/><circle cx="12" cy="12" r="10" fill="none" stroke="${color}" stroke-width="2" style="box-shadow: ${pulseShadow}; display: ${isEEZBreach ? 'block' : 'none'}; animation: ${isEEZBreach ? 'pulse 1s infinite' : 'none'};" /></svg>`;
          const customIcon = L.divIcon({ html: iconHtml, className: '', iconSize: [24, 24], iconAnchor: [12, 12] });

          // Snail trail — handle both v.history ({lat,lon}[]) and v.trail ([[lat,lon]][]) formats
          let historyCoords: [number, number][] = [];
          if (v.history && v.history.length > 1) {
            historyCoords = v.history.map((h: any) => [h.lat, h.lon] as [number, number]);
          } else if (v.trail && (v.trail as any[]).length > 1) {
            historyCoords = (v.trail as any[]).map((t: any) => 
              Array.isArray(t) ? [t[0], t[1]] as [number, number] : [t.lat, t.lon] as [number, number]
            );
          }

          // Generate simulated chart data for recent speed/threat to emulate historical telemetry
          const chartData = [
            { time: 'T-4', speed: v.speed * 0.9, threat: (v.threat_score || 0) * 0.8 },
            { time: 'T-3', speed: v.speed * 0.95, threat: (v.threat_score || 0) * 0.9 },
            { time: 'T-2', speed: v.speed * 0.8, threat: v.threat_score || 0 },
            { time: 'T-1', speed: v.speed, threat: (v.threat_score || 0) * 1.1 },
            { time: 'Now', speed: v.speed, threat: v.threat_score || 0 },
          ];

          return (
            <React.Fragment key={v.mmsi}>
              {historyCoords.length > 1 && (
                <Polyline positions={historyCoords} pathOptions={{ color: color, weight: 2, opacity: 0.5 }} />
              )}
              <Marker position={[v.lat, v.lon]} icon={customIcon}>
                <Popup className="tactical-popup">
                  <div className="font-mono text-xs w-[220px] max-h-[200px] flex flex-col overflow-y-auto p-1">
                    <div className="mb-2 border-b border-slate-700 pb-1">
                      <strong>MMSI:</strong> {v.mmsi}<br/>
                      <strong>Name:</strong> {v.name || 'UNKNOWN'}<br/>
                      <strong>Speed:</strong> {v.speed} knots<br/>
                      <strong>Heading:</strong> {v.heading}°<br/>
                      <strong>Threat Score:</strong> <span className={v.threat_score && v.threat_score >= 75 ? 'text-red-500 font-bold' : v.threat_score && v.threat_score >= 40 ? 'text-amber-500 font-bold' : 'text-emerald-500'}>{v.threat_score || 0}/100</span>
                    </div>
                    {v.anomalies && v.anomalies.length > 0 && (
                      <div className="mb-2 p-1.5 bg-red-950/60 border border-red-500/40 rounded text-[10px]">
                        <strong className="text-red-400 block mb-1">🚨 ANOMALIES ({v.anomalies.length}):</strong>
                        {v.anomalies.map((a, idx) => (
                          <div key={idx} className="text-red-300 mb-0.5 leading-tight">
                            <span className={`inline-block px-1 py-0.2 rounded text-[9px] font-bold uppercase mr-1 ${a.severity === 'CRITICAL' ? 'bg-red-600 text-white' : a.severity === 'HIGH' ? 'bg-orange-600 text-white' : 'bg-amber-600 text-white'}`}>{a.severity}</span>
                            {a.description}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="h-[60px] min-h-[60px] w-full">
                      <ResponsiveContainer width="99%" height="100%">
                        <AreaChart data={chartData}>
                          <XAxis dataKey="time" hide />
                          <YAxis hide domain={['auto', 'auto']} />
                          <RechartsTooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', fontSize: '10px', color: '#f8fafc' }} />
                          <Area type="monotone" dataKey="speed" stroke="#0056b3" fill="#0056b3" fillOpacity={0.2} />
                          <Area type="monotone" dataKey="threat" stroke="#EF4444" fill="#EF4444" fillOpacity={0.2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}

        {layers.globalSlicks && visibleSlicks.map(slick => {
          // Bounding box from coordinates
          const offset = Math.sqrt(slick.area_km2 || 1) * 0.005;
          const lat = slick.coordinates.lat;
          const lon = slick.coordinates.lon;
          const bounds = [
            [lat - offset, lon - offset],
            [lat + offset, lon - offset],
            [lat + offset, lon + offset],
            [lat - offset, lon + offset]
          ];
          
          const slickIconHtml = `<svg width="24" height="24" viewBox="0 0 24 24" style="overflow:visible;"><path d="M12,2C12,2 5,10 5,15C5,18.866 8.134,22 12,22C15.866,22 19,18.866 19,15C19,10 12,2 12,2Z" fill="rgba(245, 158, 11, 0.8)" stroke="#EF4444" stroke-width="2" style="box-shadow: 0 0 10px rgba(245,158,11,0.5); border-radius: 50%;"/></svg>`;
          const customSlickIcon = L.divIcon({ html: slickIconHtml, className: '', iconSize: [24, 24], iconAnchor: [12, 24] });
          
          return (
            <React.Fragment key={slick.id}>
              <Polygon positions={bounds as any} pathOptions={{ color: '#EF4444', weight: 2, fillColor: '#EF4444', fillOpacity: 0.2 }} />
              {/* Simulated reverse drift trajectory indicating likely origin */}
              <Polyline positions={[[lat, lon], [lat - 0.05, lon + 0.1]] as any} pathOptions={{ color: '#EF4444', weight: 2, dashArray: '5, 5' }} />
              <Marker position={[lat, lon]} icon={customSlickIcon}>
                <Popup className="tactical-popup">
                  <div className="font-mono text-xs w-[180px] text-slate-900">
                    <strong className="text-orange-600">OIL SLICK DETECTED</strong><br/>
                    <strong>Incident:</strong> {slick.id} <br/> 
                    <strong>Area:</strong> {slick.area_km2} km² <br/>
                    <strong>Confidence:</strong> {slick.confidence ? (slick.confidence * 100).toFixed(0) + '%' : 'N/A'}<br/>
                    <strong>Suspect:</strong> <span className="text-red-600">{slick.suspect_mmsi || 'UNATTRIBUTED'}</span>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}

      </MapContainer>
    </div>
  );
}
