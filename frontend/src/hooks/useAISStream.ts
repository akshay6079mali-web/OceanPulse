import { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';
import axios from 'axios';
import { API_BASE_URL } from '../App';

export interface AnomalyFlag {
  type: string;       // "LOITERING", "SPEED_ANOMALY", "COURSE_DEVIATION", "PROXIMITY", "EEZ_BREACH", "EEZ_APPROACH"
  severity: string;   // "LOW", "MEDIUM", "HIGH", "CRITICAL"
  description: string;
  value?: number;
}

export interface VesselTrack {
  mmsi: string;
  name?: string;
  callsign?: string;
  destination?: string;
  timestamp: string;
  lat: number;
  lon: number;
  speed: number;
  heading: number;
  threat_score?: number;
  in_eez?: boolean;
  history?: { lat: number, lon: number }[];
  anomalies?: AnomalyFlag[];
}

export function useAISStream(token: string | null) {
  const [isBackendOffline, setIsBackendOffline] = useState(false);
  const dvrTimeOffset = useAppStore(s => s.dvrTimeOffset);

  // Ref to track the AbortController for in-flight history requests (BUG 3 FIX)
  const abortRef = useRef<AbortController | null>(null);
  // Ref to track the debounce timer (BUG 2 FIX)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- 1. Live WebSocket Effect ---
  useEffect(() => {
    if (!token) return;

    let ws: WebSocket;
    let retryTimeout: ReturnType<typeof setTimeout>;
    let flushInterval: ReturnType<typeof setInterval>;
    let buffer: Record<string, VesselTrack> = {};

    const connect = () => {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ? '127.0.0.1:8000' : window.location.host;
      ws = new WebSocket(`${wsProtocol}//${wsHost}/api/v1/stream/ais?token=${token}`);

      ws.onopen = () => setIsBackendOffline(false);

      flushInterval = setInterval(() => {
        // Skip flushing live data if we are in historical mode or paused
        if (useAppStore.getState().dvrTimeOffset < 0 || useAppStore.getState().dvrPaused) {
          buffer = {};
          return;
        }

        if (Object.keys(buffer).length === 0) return;

        for (const mmsi in buffer) {
          const track = buffer[mmsi];
          const prevTrack = useAppStore.getState().vessels[mmsi];
          const isNewBreach = track.in_eez && (!prevTrack || !prevTrack.in_eez);

          if (isNewBreach) {
            setTimeout(() => {
              toast.error(`EEZ BREACH: MMSI ${track.mmsi}`, {
                style: { background: '#EF4444', color: '#fff', fontWeight: 600 }
              });
            }, 0);
          }
        }

        useAppStore.getState().updateVesselsBatch(buffer);
        buffer = {}; // clear buffer
      }, 1000);

      ws.onmessage = (event) => {
        // BUG 6 FIX: Don't parse WS messages when in history mode
        const state = useAppStore.getState();
        if (state.dvrTimeOffset < 0 || state.dvrPaused) return;
        
        try {
          const track: VesselTrack = JSON.parse(event.data);
          buffer[track.mmsi] = track;
        } catch (e) {
          console.error("Failed to parse message", e);
        }
      };

      ws.onclose = () => {
        setIsBackendOffline(true);
        clearInterval(flushInterval);
        retryTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      clearTimeout(retryTimeout);
      clearInterval(flushInterval);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [token]);

  // --- 2. History Fetching Effect (with debounce + abort) ---
  useEffect(() => {
    if (!token || dvrTimeOffset >= 0) return;

    // BUG 3 FIX: Cancel any in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    // BUG 2 FIX: Debounce the history fetch by 300ms
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await axios.get(
          `${API_BASE_URL}/api/v1/history/ais?time_offset_hours=${dvrTimeOffset}`,
          {
            headers: { Authorization: `Bearer ${token}` },
            signal: controller.signal
          }
        );
        
        // BUG 3 FIX: Check if this request was aborted before applying state
        if (controller.signal.aborted) return;

        const data: VesselTrack[] = res.data;
        const historyBatch: Record<string, VesselTrack> = {};
        const prevVessels = useAppStore.getState().vessels;
        
        for (const v of data) {
          const prev = prevVessels[v.mmsi];
          let newHistory = [{ lat: v.lat, lon: v.lon }];
          
          if (prev?.history && prev.history.length > 0) {
            const lastPos = prev.history[prev.history.length - 1];
            const dist = Math.hypot(lastPos.lat - v.lat, lastPos.lon - v.lon);
            if (dist < 0.05) { // about 5km — maintain continuous trail
              newHistory = [...prev.history, { lat: v.lat, lon: v.lon }].slice(-5);
            }
          }
          
          v.history = newHistory;
          historyBatch[v.mmsi] = v;
        }

        // Direct overwrite of the vessels state when scrubbing history
        useAppStore.setState({ vessels: historyBatch });
      } catch (err) {
        if (axios.isCancel(err)) return; // Aborted — this is expected
        console.error("Error fetching history:", err);
      }
    }, 300); // 300ms debounce

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [dvrTimeOffset, token]);

  return { isBackendOffline };
}
