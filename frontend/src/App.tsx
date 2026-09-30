import { useState, useEffect, useMemo } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import axios from 'axios';
import MapViewer from './components/MapViewer';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Ledger from './components/Ledger';
import LoginModal from './components/LoginModal';
import DVRScrubber from './components/DVRScrubber';
import { useAISStream } from './hooks/useAISStream';
import type { VesselTrack } from './hooks/useAISStream';
import { useAppStore } from './store';

export const API_BASE_URL = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : window.location.origin);

function App() {
  const [token, setToken] = useState<string | null>(null);
  const setSlicks = useAppStore(state => state.setSlicks);
  const setIncoisData = useAppStore(state => state.setIncoisData);
  
  const slicks = useAppStore(state => state.slicks);
  const vessels = useAppStore(state => state.vessels);
  const incoisData = useAppStore(state => state.incoisData);
  
  const [activeMode, setActiveMode] = useState<'overwatch' | 'forensic'>('overwatch');
  
  // Remove auto-login
  useEffect(() => {
    // We let the user login via LoginModal now
  }, []);

  const { isBackendOffline } = useAISStream(token);

  const [layers, setLayers] = useState({
    liveAis: true,
    globalSlicks: true,
    eezGeofence: true,
    incoisVectors: true
  });
  const [selectedIncident, setSelectedIncident] = useState<any>(null);
  const [geofenceBbox, setGeofenceBbox] = useState<string>('');
  const [isLoadingSlicks, setIsLoadingSlicks] = useState(true);
  const [isDrawingZone, setIsDrawingZone] = useState(false);
  const [sarPasses, setSarPasses] = useState<any[]>([]);

  // Poll ledger, slicks, and INCOIS
  useEffect(() => {
    if (!token) return;

    const fetchData = async () => {
      try {
        const ledgerRes = await axios.get(`${API_BASE_URL}/api/v1/slicks`, {
          headers: { Authorization: `Bearer ${token}` },
          params: geofenceBbox ? { bbox: geofenceBbox } : {}
        });
        
        setSlicks(ledgerRes.data); // Slicks and incidents are the same
      } catch (err) {
        console.error("Failed to fetch data", err);
      } finally {
        setIsLoadingSlicks(false);
      }
    };
    
    const fetchIncois = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/v1/incois/forecast`, {
          headers: { Authorization: `Bearer ${token}` },
          params: geofenceBbox ? { bbox: geofenceBbox } : {}
        });
        setIncoisData(res.data.vectors || []);
      } catch (err) {
        console.error("Failed to fetch INCOIS", err);
      }
    };

    const fetchSar = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/v1/sar/passes`, {
          headers: { Authorization: `Bearer ${token}` },
          params: geofenceBbox ? { bbox: geofenceBbox } : {}
        });
        setSarPasses(res.data || []);
      } catch (err) {
        console.error("Failed to fetch SAR", err);
      }
    };

    fetchData();
    fetchIncois();
    fetchSar();
    const interval = setInterval(() => {
      fetchData();
      fetchIncois();
      fetchSar();
    }, 10000);
    return () => clearInterval(interval);
  }, [token, geofenceBbox]);

  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Centralized Axios Error Interceptor
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          setToken(null);
          toast.error("Session expired. Please log in again.", { id: "401-error" });
        } else if (error.response) {
          toast.error(error.response.data?.detail || "An API error occurred");
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  const handleLogout = () => {
    setToken(null);
  };

  const handleRunPipeline = async (sarPath: string, aisPath: string, windSpeed: number) => {
    if (!token) return;
    setIsAnalyzing(true);
    try {
      await axios.post(`${API_BASE_URL}/api/v1/analyze`, {
        sar_path: sarPath,
        ais_path: aisPath,
        wind_speed: windSpeed
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("Pipeline triggered successfully");
    } catch (err) {
      console.error("Pipeline failed", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const bboxParts = useMemo(() => geofenceBbox ? geofenceBbox.split(',').map(Number) : null, [geofenceBbox]);
  const isBboxValid = useMemo(() => bboxParts && bboxParts.length === 4 && bboxParts.every(n => !isNaN(n)), [bboxParts]);
  const [minLon, minLat, maxLon, maxLat] = isBboxValid && bboxParts ? bboxParts : [-180, -90, 180, 90];

  const isInBbox = (lat: number, lon: number) => {
    if (!isBboxValid) return true;
    return lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon;
  };

  const visibleSlicks = useMemo(() => slicks.filter(s => isInBbox(s.coordinates.lat, s.coordinates.lon)), [slicks, isBboxValid, minLat, maxLat, minLon, maxLon]);
  const visibleVectors = useMemo(() => incoisData.filter(d => isInBbox(d.lat, d.lon)), [incoisData, isBboxValid, minLat, maxLat, minLon, maxLon]);
  
  const visibleVesselsRecord = useMemo(() => {
    const record: Record<string, VesselTrack> = {};
    Object.entries(vessels).forEach(([mmsi, v]) => {
      if (isInBbox(v.lat, v.lon)) record[mmsi] = v;
    });
    return record;
  }, [vessels, isBboxValid, minLat, maxLat, minLon, maxLon]);
  
  const visibleVesselsArray = useMemo(() => Object.values(visibleVesselsRecord), [visibleVesselsRecord]);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-slate-50 text-slate-900">
      <Toaster position="top-right" toastOptions={{ className: 'tabular-nums font-mono text-sm border border-slate-200 bg-white text-slate-900 shadow-lg' }} />
      
      {/* Background Map - z-index 0 */}
      <MapViewer 
        vessels={visibleVesselsRecord} 
        slicks={visibleSlicks} 
        layers={layers}
        incoisData={visibleVectors}
        selectedIncident={selectedIncident}
        geofenceBbox={geofenceBbox}
        setGeofenceBbox={setGeofenceBbox}
        isDrawingZone={isDrawingZone}
        setIsDrawingZone={setIsDrawingZone}
      />

      {/* Foreground HUD - z-index 1000+ */}
      <div className={`hud-container pointer-events-none ${activeMode === 'forensic' ? 'ring-4 ring-inset ring-anomaly-amber/50 bg-anomaly-amber/5' : ''}`}>
        
        {/* All actual interactive components inside HUD must have pointer-events-auto */}
        {activeMode === 'forensic' && (
          <div className="absolute top-0 left-0 w-full bg-anomaly-amber text-black text-center text-[10px] font-bold py-0.5 tracking-[0.2em] uppercase z-50">
            ⚠ WARNING: FORENSIC SANDBOX ACTIVE. LIVE OVERWATCH PAUSED. ⚠
          </div>
        )}

        {/* Top Slot */}
        <div className="w-full pointer-events-auto">
          <Header isBackendOffline={isBackendOffline} onLogout={handleLogout} />
        </div>

        <div className="flex-1 mt-2">
          <Sidebar vessels={visibleVesselsRecord} layers={layers} setLayers={setLayers} onRunPipeline={handleRunPipeline} isAnalyzing={isAnalyzing} geofenceBbox={geofenceBbox} setGeofenceBbox={setGeofenceBbox} isDrawingZone={isDrawingZone} setIsDrawingZone={setIsDrawingZone} activeMode={activeMode} setActiveMode={setActiveMode} />
        </div>

        {/* Bottom Slot */}
        <div className="w-full flex flex-col items-center">
          <DVRScrubber />
          <Ledger 
            incidents={visibleSlicks} 
            onSelectIncident={setSelectedIncident} 
            isLoading={isLoadingSlicks} 
            vessels={visibleVesselsArray} 
            passes={sarPasses} 
            vectors={visibleVectors} 
            onFlyToTarget={(target) => setSelectedIncident({ coordinates: { lat: target.lat, lon: target.lon } })} 
            activeMode={activeMode}
            token={token}
          />
        </div>
      </div>

      {!token && <LoginModal onLogin={setToken} />}
    </div>
  );
}

export default App;
