import React, { useEffect, useRef } from 'react';
import { Play, Pause, SkipBack } from 'lucide-react';
import { useAppStore } from '../store';

export default function DVRScrubber() {
  const dvrTimeOffset = useAppStore(s => s.dvrTimeOffset);
  const dvrPlaying = useAppStore(s => s.dvrPlaying);
  const dvrSpeed = useAppStore(s => s.dvrSpeed);
  const dvrPaused = useAppStore(s => s.dvrPaused);
  const setDvrTimeOffset = useAppStore(s => s.setDvrTimeOffset);
  const setDvrPlaying = useAppStore(s => s.setDvrPlaying);
  const setDvrSpeed = useAppStore(s => s.setDvrSpeed);
  const setDvrPaused = useAppStore(s => s.setDvrPaused);

  const playbackRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Slider value: 0 = -24h, 1440 = LIVE (0 offset)
  // Each step = 1 minute of history
  const sliderValue = Math.round((dvrTimeOffset + 24) * 60);

  const isLive = dvrTimeOffset === 0;

  // Format the current time label
  const getTimeLabel = () => {
    if (isLive) return 'LIVE';
    const hours = Math.abs(dvrTimeOffset);
    if (hours < 1) return `-${Math.round(hours * 60)}m`;
    return `-${hours.toFixed(1)}h`;
  };

  // FIX BUG 1 + 4 + 7:
  // - Removed `dvrTimeOffset` from deps (was causing infinite effect loop)
  // - Added `dvrSpeed` to deps (speed change was being ignored)
  // - Read current offset from store inside interval (avoids stale closure)
  useEffect(() => {
    if (playbackRef.current) {
      clearInterval(playbackRef.current);
      playbackRef.current = null;
    }

    if (dvrPlaying) {
      // Read current state from the store, not from stale closure
      const currentOffset = useAppStore.getState().dvrTimeOffset;
      
      if (currentOffset < 0) {
        // Historical mode: advance timeline
        playbackRef.current = setInterval(() => {
          const state = useAppStore.getState();
          const current = state.dvrTimeOffset;
          
          if (current >= 0) {
            // Already at live — stop
            if (playbackRef.current) clearInterval(playbackRef.current);
            playbackRef.current = null;
            state.setDvrTimeOffset(0);
            state.setDvrPaused(false);
            state.setDvrPlaying(true);
            return;
          }
          
          // Each tick: advance by (speed) minutes, converted to hours
          const jumpHours = state.dvrSpeed / 60;
          const newOffset = Math.min(0, current + jumpHours);
          state.setDvrTimeOffset(newOffset);
          
          if (newOffset >= 0) {
            // Reached live — switch to live mode
            if (playbackRef.current) clearInterval(playbackRef.current);
            playbackRef.current = null;
            state.setDvrTimeOffset(0);
            state.setDvrPaused(false);
            state.setDvrPlaying(true);
          }
        }, 500);
      }
      // If at live (offset >= 0) and playing, we just let the WS stream
    }

    return () => {
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
        playbackRef.current = null;
      }
    };
  }, [dvrPlaying, dvrSpeed]); // BUG 1 FIX: no dvrTimeOffset. BUG 7 FIX: includes dvrSpeed

  // FIX BUG 5: Slider range 0-1440 for minute-level granularity
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    // Convert slider value (0-1440) to hours offset (-24 to 0)
    const offset = (val / 60) - 24;
    // Round to nearest minute (1/60 hour)
    const rounded = Math.round(offset * 60) / 60;
    
    setDvrTimeOffset(rounded);
    
    if (rounded < 0) {
      setDvrPaused(true); // Pause live updates when scrubbing history
      setDvrPlaying(false); // Pause historical playback when manually dragged
    } else {
      setDvrPaused(false); // Resume live at 0
      setDvrPlaying(true);
    }
  };

  const handlePlayPause = () => {
    if (isLive) {
      // At live position: toggle pause/resume of live vessel updates
      if (dvrPlaying) {
        setDvrPlaying(false);
        setDvrPaused(true);
      } else {
        setDvrPlaying(true);
        setDvrPaused(false);
      }
    } else {
      // In historical mode: toggle playback
      setDvrPlaying(!dvrPlaying);
    }
  };

  const handleSkipBack = () => {
    const newOffset = Math.max(-24, dvrTimeOffset - 1);
    setDvrTimeOffset(newOffset);
    setDvrPaused(true);
    setDvrPlaying(false);
  };

  const handleLive = () => {
    setDvrTimeOffset(0);
    setDvrPaused(false);
    setDvrPlaying(true);
  };

  const handleSpeed = (s: number) => {
    setDvrSpeed(s);
  };

  return (
    <div className="h-[40px] w-full max-w-[560px] mx-auto mb-2 rounded-full bg-white/95 border border-slate-200 flex items-center px-4 space-x-3 pointer-events-auto shadow-lg backdrop-blur-sm justify-between">
      
      <button onClick={handlePlayPause} className="text-slate-600 hover:text-[#0056b3] transition" title={dvrPlaying ? "Pause" : "Play"}>
        {dvrPlaying ? <Pause size={18} /> : <Play size={18} />}
      </button>
      
      <button onClick={handleSkipBack} className="text-slate-600 hover:text-[#0056b3] transition" title="Skip back 1 hour">
        <SkipBack size={18} />
      </button>

      <div className="flex space-x-1 bg-slate-100 rounded-full p-1">
        {[1, 2, 5].map((s) => (
          <button
            key={s}
            onClick={() => handleSpeed(s)}
            className={`text-xs px-2 py-0.5 rounded-full transition ${dvrSpeed === s ? 'bg-[#0056b3] text-white' : 'text-slate-500 hover:text-slate-900'}`}
          >
            {s}x
          </button>
        ))}
      </div>

      <div className="flex items-center space-x-2 text-xs text-slate-500 font-mono flex-1 min-w-0">
        <span className="shrink-0">-24h</span>
        <input 
          type="range" 
          min="0" 
          max="1440" 
          step="1"
          value={sliderValue}
          onChange={handleSliderChange}
          className="w-full accent-[#0056b3] h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer" 
        />
        <span className="shrink-0 w-10 text-right">{getTimeLabel()}</span>
      </div>

      <button 
        onClick={handleLive}
        className={`flex items-center space-x-1 text-xs font-bold transition shrink-0 ${isLive && !dvrPaused ? 'text-[#0056b3]' : 'text-slate-400 hover:text-[#0056b3]'}`}
      >
        <span className={`inline-block w-2 h-2 rounded-full mr-1 ${isLive && !dvrPaused ? 'bg-[#0056b3] animate-pulse' : 'bg-slate-300'}`}></span>
        <span>LIVE</span>
      </button>
    </div>
  );
}
