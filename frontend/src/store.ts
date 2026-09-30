import { create } from 'zustand';
import type { VesselTrack } from './hooks/useAISStream';

interface AppState {
  vessels: Record<string, VesselTrack>;
  slicks: any[];
  incoisData: any[];
  
  // DVR Scrubber state
  dvrTimeOffset: number; // 0 = LIVE, -1 to -24 = hours in the past
  dvrPlaying: boolean;
  dvrSpeed: number; // 1, 2, or 5
  dvrPaused: boolean; // true = live updates paused on map
  
  setSlicks: (slicks: any[]) => void;
  setIncoisData: (data: any[]) => void;
  updateVesselsBatch: (buffer: Record<string, VesselTrack>) => void;
  setDvrTimeOffset: (offset: number) => void;
  setDvrPlaying: (playing: boolean) => void;
  setDvrSpeed: (speed: number) => void;
  setDvrPaused: (paused: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  vessels: {},
  slicks: [],
  incoisData: [],
  dvrTimeOffset: 0,
  dvrPlaying: true,
  dvrSpeed: 1,
  dvrPaused: false,
  
  setSlicks: (slicks) => set({ slicks }),
  setIncoisData: (incoisData) => set({ incoisData }),
  
  updateVesselsBatch: (buffer) => set((state) => {
    // If DVR is paused (user scrubbing history), don't update live vessels
    if (state.dvrPaused) return state;
    
    const updated = { ...state.vessels };
    let hasChanges = false;
    
    for (const mmsi in buffer) {
      const track = buffer[mmsi];
      const prevTrack = updated[mmsi];
      
      const newHistory = prevTrack?.history 
        ? [...prevTrack.history, { lat: track.lat, lon: track.lon }].slice(-5) 
        : [{ lat: track.lat, lon: track.lon }];
        
      updated[mmsi] = { ...track, history: newHistory };
      hasChanges = true;
    }
    
    if (!hasChanges) return state;
    return { vessels: updated };
  }),
  
  setDvrTimeOffset: (dvrTimeOffset) => set({ dvrTimeOffset }),
  setDvrPlaying: (dvrPlaying) => set({ dvrPlaying }),
  setDvrSpeed: (dvrSpeed) => set({ dvrSpeed }),
  setDvrPaused: (dvrPaused) => set({ dvrPaused }),
}));

