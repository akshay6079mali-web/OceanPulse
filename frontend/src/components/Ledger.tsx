import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, X, Download, ShieldAlert, Crosshair } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../App';

interface Incident {
  id: string;
  suspect_mmsi?: string;
  timestamp: string;
  confidence: number;
  coordinates?: { lat: number; lon: number };
  area_km2?: number;
  scene_id?: string;
}

interface LedgerProps {
  incidents: Incident[];
  onSelectIncident?: (incident: Incident) => void;
  isLoading?: boolean;
  vessels?: any[];
  passes?: any[];
  vectors?: any[];
  onFlyToTarget?: (target: { lat: number, lon: number, zoom: number }) => void;
  activeMode: 'overwatch' | 'forensic';
  token?: string | null;
}

export default function Ledger({ incidents, onSelectIncident, isLoading = false, vessels = [], passes = [], vectors = [], onFlyToTarget, activeMode, token }: LedgerProps) {
  const [activeTab, setActiveTab] = useState<'slicks' | 'ais' | 'sar' | 'weather'>('slicks');
  const [selectedSarScene, setSelectedSarScene] = useState<any>(null);
  const [selectedSarIncident, setSelectedSarIncident] = useState<any>(null);
  const [sarDetails, setSarDetails] = useState<any>(null);

  useEffect(() => {
    if (selectedSarScene && token) {
      const lat = selectedSarIncident?.coordinates?.lat || 18.93;
      const lon = selectedSarIncident?.coordinates?.lon || 72.50;
      const area = selectedSarIncident?.area_km2 || 4.5;
      const mmsi = selectedSarIncident?.suspect_mmsi || 'UNATTRIBUTED';
      axios.get(`${API_BASE_URL}/api/v1/sar/scene-details?id=${selectedSarScene}&lat=${lat}&lon=${lon}&area=${area}&mmsi=${mmsi}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(r => setSarDetails(r.data))
        .catch(console.error);
    } else {
      setSarDetails(null);
    }
  }, [selectedSarScene, token]);

  const handleExport = () => {
    if (token) {
      window.open(`${API_BASE_URL}/api/v1/export/slicks?token=${token}`, '_blank');
    }
  };

  const renderTabs = () => (
    <div className="flex gap-4 text-xs font-mono mb-2">
      <button onClick={() => setActiveTab('slicks')} className={`flex items-center gap-1 pb-1 ${activeTab === 'slicks' ? 'text-[#0056b3] border-b-2 border-[#0056b3] font-bold' : 'text-slate-500 hover:text-slate-900'}`}>Oil Slicks ({incidents.length})</button>
      <button onClick={() => setActiveTab('ais')} className={`flex items-center gap-1 pb-1 ${activeTab === 'ais' ? 'text-[#0056b3] border-b-2 border-[#0056b3] font-bold' : 'text-slate-500 hover:text-slate-900'}`}>Live AIS ({vessels.length})</button>
      <button onClick={() => setActiveTab('sar')} className={`flex items-center gap-1 pb-1 ${activeTab === 'sar' ? 'text-[#0056b3] border-b-2 border-[#0056b3] font-bold' : 'text-slate-500 hover:text-slate-900'}`}>SAR Passes ({passes.length})</button>
      <button onClick={() => setActiveTab('weather')} className={`flex items-center gap-1 pb-1 ${activeTab === 'weather' ? 'text-[#0056b3] border-b-2 border-[#0056b3] font-bold' : 'text-slate-500 hover:text-slate-900'}`}>Metocean ({vectors.length})</button>
    </div>
  );

  return (
    <div className={`panel ledger tactical-panel w-full p-4 mx-auto flex flex-col transition-all duration-300 ${activeMode === 'forensic' ? 'border-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.15)] ring-1 ring-orange-500/30' : ''}`} style={{ maxHeight: '175px' }}>
      <div className="flex justify-between items-center border-b border-slate-200 pb-2 mb-2">
        {renderTabs()}
        <div className="flex items-center gap-2">
          {activeTab === 'slicks' && <button onClick={handleExport} className="tactical-btn font-mono text-xs">[EXPORT CSV]</button>}
          <button className="tactical-btn"><ChevronDown className="w-4 h-4" /></button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {activeTab === 'slicks' && (
          <table className="w-full text-xs text-left border-collapse">
            <thead className="text-[10px] uppercase text-slate-500 sticky top-0 bg-white z-10 border-b border-slate-200 shadow-sm">
              <tr>
                <th className="py-2 px-1 font-semibold">ID</th>
                <th className="py-2 px-1 font-semibold">Timestamp</th>
                <th className="py-2 px-1 font-semibold">Coordinates</th>
                <th className="py-2 px-1 font-semibold text-right">Area (km²)</th>
                <th className="py-2 px-1 font-semibold text-right">Suspect MMSI</th>
                <th className="py-2 px-1 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {isLoading && incidents.length === 0 ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i} className="animate-pulse border-b border-slate-200">
                    <td className="py-2 px-1"><div className="h-3 bg-slate-200 rounded w-8"></div></td>
                    <td className="py-2 px-1"><div className="h-3 bg-slate-200 rounded w-32"></div></td>
                    <td className="py-2 px-1"><div className="h-3 bg-slate-200 rounded w-24"></div></td>
                    <td className="py-2 px-1 flex justify-end"><div className="h-3 bg-slate-200 rounded w-16"></div></td>
                    <td className="py-2 px-1"><div className="h-3 bg-slate-200 rounded w-20 float-right"></div></td>
                  </tr>
                ))
              ) : incidents.length === 0 ? (
                <tr><td colSpan={6} className="py-4 text-center text-slate-500">No oil slick incidents detected in this zone.</td></tr>
              ) : (
                incidents.map((incident) => (
                  <tr
                    key={incident.id}
                    className="border-b border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => onSelectIncident?.(incident)}
                  >
                    <td className="py-2 px-1">{incident.id}</td>
                    <td className="py-2 px-1 text-slate-500">{new Date(incident.timestamp).toUTCString()}</td>
                    <td className="py-2 px-1 text-slate-900 font-medium">{incident.coordinates ? `${incident.coordinates.lat.toFixed(2)}° N, ${incident.coordinates.lon.toFixed(2)}° E` : 'N/A'}</td>
                    <td className="py-2 px-1 text-right">{incident.area_km2 ? `${incident.area_km2.toFixed(2)} km²` : 'N/A'}</td>
                    <td className="py-2 px-1 text-right font-bold">
                      {incident.suspect_mmsi ? (
                        <span className="px-2 py-0.5 rounded bg-red-50 text-red-600 border border-red-100">{incident.suspect_mmsi}</span>
                      ) : 'N/A'}
                    </td>
                    <td className="py-2 px-1 text-right">
                      <button className="tactical-btn text-[#0056b3] hover:text-blue-800" onClick={(e) => { e.stopPropagation(); setSelectedSarIncident(incident); setSelectedSarScene(incident.scene_id || `S1A_IW_${incident.id}`); }}>[View SAR]</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
        {activeTab === 'ais' && (
          <table className="w-full text-xs text-left border-collapse">
            <thead className="text-[10px] uppercase text-slate-500 sticky top-0 bg-white z-10 border-b border-slate-200 shadow-sm">
              <tr>
                <th className="py-2 px-1 font-semibold">MMSI</th>
                <th className="py-2 px-1 font-semibold">Ship Name</th>
                <th className="py-2 px-1 font-semibold">Speed (kt)</th>
                <th className="py-2 px-1 font-semibold">Heading</th>
                <th className="py-2 px-1 font-semibold">Live Coordinates (Lat, Lon)</th>
                <th className="py-2 px-1 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {vessels.length === 0 ? (
                <tr><td colSpan={6} className="py-4 text-center text-slate-500">No vessels found.</td></tr>
              ) : (
                vessels.map(v => (
                  <tr key={v.mmsi} className="border-b border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => onFlyToTarget?.({ lat: v.lat, lon: v.lon, zoom: 10 })}>
                    <td className="py-2 px-1">{v.mmsi}</td>
                    <td className="py-2 px-1 font-bold text-emerald-600">{v.name || 'UNKNOWN'}</td>
                    <td className="py-2 px-1">{v.speed}</td>
                    <td className="py-2 px-1">{v.heading}°</td>
                    <td className="py-2 px-1 text-slate-900 font-medium">{v.lat.toFixed(4)}, {v.lon.toFixed(4)}</td>
                    <td className="py-2 px-1 text-right"><button className="tactical-btn text-[#0056b3] hover:text-blue-800" onClick={(e) => { e.stopPropagation(); onFlyToTarget?.({ lat: v.lat, lon: v.lon, zoom: 10 }); }}>[ Fly to Ship ]</button></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
        {activeTab === 'sar' && (
          <table className="w-full text-xs text-left border-collapse">
            <thead className="text-[10px] uppercase text-slate-500 sticky top-0 bg-white z-10 border-b border-slate-200 shadow-sm">
              <tr>
                <th className="py-2 px-1 font-semibold">Mission ID</th>
                <th className="py-2 px-1 font-semibold">Satellite Name</th>
                <th className="py-2 px-1 font-semibold text-right">Acquisition Time</th>
                <th className="py-2 px-1 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {passes.length === 0 ? (
                <tr><td colSpan={4} className="py-4 text-center text-slate-500">No recent SAR passes detected in this sector.</td></tr>
              ) : (
                passes.map((p, idx) => (
                  <tr key={p.id || idx} className="border-b border-slate-200 hover:bg-slate-50 transition-colors">
                    <td className="py-2 px-1">{p.id}</td>
                    <td className="py-2 px-1 text-slate-900 font-medium">{p.name}</td>
                    <td className="py-2 px-1 text-right">{new Date(p.timestamp).toUTCString()}</td>
                    <td className="py-2 px-1 text-right"><button className="tactical-btn text-[#0056b3] hover:text-blue-800" onClick={(e) => { e.stopPropagation(); setSelectedSarScene(p.id); }}>[View SAR Data]</button></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
        {activeTab === 'weather' && (
          <table className="w-full text-xs text-left border-collapse">
            <thead className="text-[10px] uppercase text-slate-500 sticky top-0 bg-white z-10 border-b border-slate-200 shadow-sm">
              <tr>
                <th className="py-2 px-1 font-semibold">Lat</th>
                <th className="py-2 px-1 font-semibold">Lon</th>
                <th className="py-2 px-1 font-semibold">U (m/s)</th>
                <th className="py-2 px-1 font-semibold">V (m/s)</th>
                <th className="py-2 px-1 font-semibold text-right">Speed (m/s)</th>
                <th className="py-2 px-1 font-semibold text-right">Direction (°)</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {vectors.length === 0 ? (
                <tr><td colSpan={6} className="py-4 text-center text-slate-500">No metocean data available for this zone.</td></tr>
              ) : (
                vectors.map((v: any, idx: number) => (
                  <tr key={idx} className="border-b border-slate-200 hover:bg-slate-50 transition-colors">
                    <td className="py-2 px-1">{v.lat?.toFixed(2)}</td>
                    <td className="py-2 px-1">{v.lon?.toFixed(2)}</td>
                    <td className="py-2 px-1">{v.u?.toFixed(3)}</td>
                    <td className="py-2 px-1">{v.v?.toFixed(3)}</td>
                    <td className="py-2 px-1 text-right">{v.speed?.toFixed(3)}</td>
                    <td className="py-2 px-1 text-right">{v.direction?.toFixed(1)}°</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {selectedSarScene && sarDetails && createPortal(
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-start justify-center pt-24 z-[9999] p-4 hud-interactive">
          <div className="bg-white border border-slate-200 p-6 max-w-4xl w-full text-slate-900 shadow-2xl relative rounded-md">
            <button onClick={() => setSelectedSarScene(null)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-900">
              <X className="w-6 h-6" />
            </button>
            <h2 className="text-xl font-bold font-mono text-[#0056b3] mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-red-500" /> SAR FORENSIC OVERWATCH: {selectedSarScene}
            </h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <img src={`${API_BASE_URL}${sarDetails.quicklook_url}?token=${token}&v=${Date.now()}`} alt="SAR Quicklook" className="w-full border border-slate-200 object-contain bg-slate-50 h-64 mb-4 rounded" />
                <div className="flex gap-2">
                  <button className="flex-1 bg-[#0056b3] text-white font-bold font-mono py-2 rounded hover:bg-blue-800 flex items-center justify-center gap-2 transition" onClick={() => window.open(`${API_BASE_URL}${sarDetails.report_url}?token=${token}`, '_blank')}>
                    <Download className="w-4 h-4" /> EXPORT LEGAL REPORT
                  </button>
                  <button className="flex-1 border border-[#0056b3] text-[#0056b3] font-bold font-mono py-2 rounded hover:bg-blue-50 flex items-center justify-center gap-2 transition" onClick={() => { setSelectedSarScene(null); onFlyToTarget?.({ lat: 18.93, lon: 72.50, zoom: 11 }); }}>
                    <Crosshair className="w-4 h-4" /> FLY TO COORDINATES
                  </button>
                </div>
              </div>
              <div className="font-mono text-xs text-slate-600 space-y-4">
                <div className="p-3 bg-slate-50 rounded border border-slate-200 shadow-sm">
                  <p><strong className="text-slate-900">SATELLITE:</strong> {sarDetails.satellite}</p>
                  <p><strong className="text-slate-900">SENSOR MODE:</strong> {sarDetails.sensor_mode}</p>
                  <p><strong className="text-slate-900">POLARIZATION:</strong> {sarDetails.polarization}</p>
                  <p><strong className="text-slate-900">RESOLUTION:</strong> {sarDetails.resolution}</p>
                  <p><strong className="text-slate-900">CALIBRATION DB:</strong> {sarDetails.calibration_db}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-slate-200 shadow-sm">
                  <p><strong className="text-slate-900">INTEGRITY HASH (SHA-256):</strong></p>
                  <p className="text-emerald-600 break-all">{sarDetails.integrity_hash}</p>
                </div>
                <div className="text-slate-500 italic">
                  Prototype demonstration data. Simulated SAR quicklook generated dynamically. Real integration requires ESA SNAP toolkit and Copernicus Sentinel data hub access.
                </div>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
