import { useState, useEffect } from 'react';
import { Activity, ShieldAlert, Navigation, Menu, X } from 'lucide-react';
import type { VesselTrack } from '../hooks/useAISStream';

interface SidebarProps {
  vessels: Record<string, VesselTrack>;
  layers: { liveAis: boolean, globalSlicks: boolean, eezGeofence: boolean, incoisVectors: boolean };
  setLayers: (layers: any) => void;
  onRunPipeline?: (sarPath: string, aisPath: string, windSpeed: number) => void;
  isAnalyzing?: boolean;
  geofenceBbox: string;
  setGeofenceBbox: (bbox: string) => void;
  isDrawingZone?: boolean;
  setIsDrawingZone?: (v: boolean) => void;
  activeMode: 'overwatch' | 'forensic';
  setActiveMode: (mode: 'overwatch' | 'forensic') => void;
}

export default function Sidebar({ vessels, layers, setLayers, onRunPipeline, isAnalyzing, geofenceBbox, setGeofenceBbox, isDrawingZone, setIsDrawingZone, activeMode, setActiveMode }: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [localBbox, setLocalBbox] = useState(geofenceBbox);

  useEffect(() => {
    setLocalBbox(geofenceBbox);
  }, [geofenceBbox]);

  useEffect(() => {
    const handleObserved = (e: any) => setLocalBbox(e.detail);
    window.addEventListener('current-view-observed', handleObserved);
    return () => window.removeEventListener('current-view-observed', handleObserved);
  }, []);

  const activeCount = Object.keys(vessels).length;
  const threatCount = Object.values(vessels).filter(v => (v.threat_score || 0) >= 50 || v.in_eez === true).length;

  const [sarPath, setSarPath] = useState("data/bombay_sar_usa.tiff");
  const [aisPath, setAisPath] = useState("data/sample_ais.csv");
  const [windSpeed, setWindSpeed] = useState(5);

  const toggleLayer = (layer: keyof typeof layers) => {
    setLayers((prev: any) => ({ ...prev, [layer]: !prev[layer] }));
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="pointer-events-auto bg-white border border-slate-200 text-slate-900 p-2 rounded shadow hover:bg-slate-50 flex flex-col gap-1 items-center justify-center w-10 h-10"
        title="Open Sidebar"
      >
        <Menu size={20} />
      </button>
    );
  }

  return (
    <div className="panel sidebar tactical-panel w-[340px] flex flex-col p-3 space-y-2.5 pointer-events-auto shadow-xl transition-all duration-300" style={{ maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}>
      <div className="flex justify-between items-center mb-2 border-b border-slate-200 pb-2 shrink-0">
        <h2 className="text-sm uppercase tracking-widest font-bold text-slate-500">OceanPulse Control</h2>
        <button onClick={() => setIsOpen(false)} className="text-slate-500 hover:text-slate-900">
          <X size={18} />
        </button>
      </div>

      <div className="relative flex bg-slate-100 rounded-full p-1 border border-slate-200 mb-2 shrink-0">
        <div
          className="absolute top-1 bottom-1 bg-white rounded-full transition-all duration-300 ease-in-out shadow-sm"
          style={{
            width: 'calc(50% - 4px)',
            left: activeMode === 'overwatch' ? '4px' : 'calc(50%)',
          }}
        ></div>
        <button
          className={`relative z-10 w-1/2 py-1.5 rounded-full text-xs font-bold transition-colors duration-300 ${activeMode === 'overwatch' ? 'text-[#0056b3]' : 'text-slate-500 hover:text-slate-900'}`}
          onClick={() => setActiveMode('overwatch')}
        >Live Overwatch</button>
        <button
          className={`relative z-10 w-1/2 py-1.5 rounded-full text-xs font-bold transition-colors duration-300 ${activeMode === 'forensic' ? 'text-[#0056b3]' : 'text-slate-500 hover:text-slate-900'}`}
          onClick={() => setActiveMode('forensic')}
        >Forensic Sandbox</button>
      </div>

      <div className="bg-white border border-slate-200 p-3 rounded mb-2 shrink-0 shadow-sm">
        <h3 className="text-xs uppercase tracking-widest font-bold text-[#0056b3] mb-2 flex items-center gap-1">Select Area to Observe</h3>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <button
            onClick={() => setIsDrawingZone?.(!isDrawingZone)}
            className={`tactical-btn text-[10px] ${isDrawingZone ? 'bg-[#0056b3] text-white border-[#0056b3] font-bold' : ''}`}
          >
            Draw Zone
          </button>
          <button
            onClick={() => window.dispatchEvent(new CustomEvent('observe-current-view'))}
            className="tactical-btn text-[10px]"
          >
            Current View
          </button>
        </div>
        <select
          className="w-full text-[10px] font-mono bg-white border border-slate-200 p-1.5 rounded mb-2 text-slate-900 focus:outline-none focus:border-[#0056b3] appearance-none"
          onChange={(e) => {
            if (e.target.value) {
              setLocalBbox(e.target.value);
              setGeofenceBbox(e.target.value);
              window.dispatchEvent(new CustomEvent('fly-to-bbox', { detail: e.target.value }));
            }
          }}
          style={{ WebkitAppearance: 'none', MozAppearance: 'none' }}
        >
          <option value="" className="bg-white text-slate-900">Quick Ocean Presets...</option>
          <option value="-180,-60,180,75" className="bg-white text-slate-900">Global View (All Oceans)</option>
          <option value="14.0,54.5,23.5,60.2" className="bg-white text-slate-900">Baltic Sea Open Water</option>
          <option value="70.5,18.2,72.65,19.8" className="bg-white text-slate-900">Arabian Sea / Mumbai Offshore</option>
          <option value="50.0,24.0,56.5,27.5" className="bg-white text-slate-900">Persian Gulf / Hormuz</option>
          <option value="36.0,16.0,41.5,26.0" className="bg-white text-slate-900">Red Sea Shipping Lane</option>
          <option value="-95.0,22.0,-80.0,30.0" className="bg-white text-slate-900">Gulf of Mexico & Atlantic</option>
        </select>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <input type="text" placeholder="Min Lon" value={localBbox.split(',')[0] || ''} onChange={e => { const p = localBbox.split(','); p[0] = e.target.value; setLocalBbox(p.join(',')); }} className="w-full text-xs bg-white border border-slate-200 p-1 rounded focus:border-[#0056b3] text-slate-900" />
          <input type="text" placeholder="Min Lat" value={localBbox.split(',')[1] || ''} onChange={e => { const p = localBbox.split(','); p[1] = e.target.value; setLocalBbox(p.join(',')); }} className="w-full text-xs bg-white border border-slate-200 p-1 rounded focus:border-[#0056b3] text-slate-900" />
          <input type="text" placeholder="Max Lon" value={localBbox.split(',')[2] || ''} onChange={e => { const p = localBbox.split(','); p[2] = e.target.value; setLocalBbox(p.join(',')); }} className="w-full text-xs bg-white border border-slate-200 p-1 rounded focus:border-[#0056b3] text-slate-900" />
          <input type="text" placeholder="Max Lat" value={localBbox.split(',')[3] || ''} onChange={e => { const p = localBbox.split(','); p[3] = e.target.value; setLocalBbox(p.join(',')); }} className="w-full text-xs bg-white border border-slate-200 p-1 rounded focus:border-[#0056b3] text-slate-900" />
        </div>
        <button onClick={() => { setGeofenceBbox(localBbox); window.dispatchEvent(new CustomEvent('fly-to-bbox', { detail: localBbox })); }} className="tactical-btn w-full text-xs border-slate-200 text-[#0056b3] hover:bg-slate-100 font-semibold">Apply Coordinates</button>
      </div>

      <div className="grid grid-cols-2 gap-2 shrink-0">
        <div className="bg-white rounded p-2 border border-slate-200 shadow-sm">
          <div className="text-[10px] uppercase text-slate-500 flex items-center gap-1 mb-1">
            <Activity className="w-3 h-3" /> Active
          </div>
          <div className="text-xl font-bold tabular-nums text-blue-600">{activeCount}</div>
        </div>
        <div className="bg-white rounded p-2 border border-slate-200 shadow-sm">
          <div className="text-[10px] uppercase text-slate-500 flex items-center gap-1 mb-1">
            <ShieldAlert className="w-3 h-3 text-red-500" /> Threat
          </div>
          <div className="text-xl font-bold tabular-nums text-red-600">{threatCount}</div>
        </div>
      </div>

      <div className="space-y-2 text-[11px] shrink-0 text-slate-700">
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={layers.liveAis} onChange={() => toggleLayer('liveAis')} /> Live AIS Stream</label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={layers.globalSlicks} onChange={() => toggleLayer('globalSlicks')} /> Global Slicks</label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={layers.eezGeofence} onChange={() => toggleLayer('eezGeofence')} /> EEZ Geofence</label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={layers.incoisVectors} onChange={() => toggleLayer('incoisVectors')} /> INCOIS Vectors</label>
      </div>

      {activeMode === 'forensic' && (
        <>
          <div className="mb-2 pb-2 border-b border-slate-200 mt-2">
            <h3 className="text-[11px] uppercase tracking-widest font-bold text-[#0056b3] mb-1">Polluter Identification Workflow</h3>
            <p className="text-[10px] text-slate-500">Combine radar data with vessel traffic reports to identify potential polluters.</p>
          </div>

          <div className="space-y-4 shrink-0 mt-2">
            <div>
              <label className="block text-[10px] uppercase font-semibold text-slate-800 mb-1">
                1. Oil Spill Detection (SAR)
              </label>
              <div className="flex gap-1">
                <input type="text" value={sarPath} onChange={(e) => setSarPath(e.target.value)} placeholder="/path/to/sar.tiff" className="flex-1 min-w-0 text-xs bg-white border border-slate-200 p-1.5 rounded focus:outline-none focus:border-[#0056b3] text-slate-900 transition-colors" />
                <label className="cursor-pointer bg-slate-100 border border-slate-200 text-slate-600 px-2 rounded flex items-center justify-center text-[10px] hover:bg-slate-200 transition-colors shrink-0">
                  FILE
                  <input type="file" accept=".tiff" onChange={(e) => setSarPath(e.target.files?.[0]?.name || sarPath)} className="hidden" />
                </label>
              </div>
            </div>

            <div>
              <label className="block text-[10px] uppercase font-semibold text-slate-800 mb-1">
                2. Vessel Tracking (AIS)
              </label>
              <div className="flex gap-1">
                <input type="text" value={aisPath} onChange={(e) => setAisPath(e.target.value)} placeholder="/path/to/ais.csv" className="flex-1 min-w-0 text-xs bg-white border border-slate-200 p-1.5 rounded focus:outline-none focus:border-[#0056b3] text-slate-900 transition-colors" />
                <label className="cursor-pointer bg-slate-100 border border-slate-200 text-slate-600 px-2 rounded flex items-center justify-center text-[10px] hover:bg-slate-200 transition-colors shrink-0">
                  FILE
                  <input type="file" accept=".csv" onChange={(e) => setAisPath(e.target.files?.[0]?.name || aisPath)} className="hidden" />
                </label>
              </div>
            </div>

            <div>
              <label className="block text-[10px] uppercase font-semibold text-slate-800 mb-1">3. Metocean Data (Wind Knots)</label>
              <input type="number" value={windSpeed} onChange={(e) => setWindSpeed(Number(e.target.value))} className="w-full text-xs bg-white border border-slate-200 p-1.5 rounded focus:outline-none focus:border-[#0056b3] text-slate-900 transition-colors" />
            </div>
          </div>

          <button
            onClick={() => onRunPipeline?.(sarPath, aisPath, windSpeed)}
            disabled={isAnalyzing}
            className={`mt-4 w-full flex items-center justify-center gap-2 py-2 text-[11px] font-bold uppercase tracking-wider rounded transition-colors shrink-0 ${isAnalyzing ? 'bg-slate-200 text-slate-400 cursor-not-allowed' : 'bg-[#0056b3] text-white hover:bg-blue-800'}`}
          >
            {isAnalyzing ? 'Processing Data...' : 'Correlate & Identify Polluter'}
          </button>
        </>
      )}

      {activeMode === 'overwatch' && (
        <>
          <h3 className="text-[10px] uppercase tracking-widest font-bold mb-2 text-slate-500 shrink-0 mt-2">Active Targets</h3>
          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-2">
            {Object.values(vessels).map(v => (
              <div key={v.mmsi} className="bg-white rounded p-2 text-xs border border-slate-200 border-l-[3px] transition-colors hover:border-[#0056b3] cursor-pointer shadow-sm"
                style={{ borderLeftColor: (v.threat_score || 0) >= 75 ? '#EF4444' : (v.threat_score || 0) >= 40 ? '#F59E0B' : '#E2E8F0' }}>
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono font-bold text-slate-900">{v.name || v.mmsi}</span>
                  {v.threat_score !== undefined && (
                    <span className={`px-1.5 rounded-sm font-bold tabular-nums ${v.threat_score >= 75 ? 'bg-red-50 text-red-600' : v.threat_score >= 40 ? 'bg-orange-50 text-orange-600' : 'bg-slate-50 text-slate-500'}`}>
                      {v.threat_score} / 100
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-slate-500 font-mono text-[10px]">
                  <span className="flex items-center gap-1"><Navigation className="w-3 h-3" /> {v.speed}kt</span>
                  <span>{v.heading}°</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

    </div>
  );
}
