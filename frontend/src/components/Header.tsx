import { Search, Lock } from 'lucide-react';

interface HeaderProps {
  isBackendOffline: boolean;
  onLogout: () => void;
}

export default function Header({ isBackendOffline, onLogout }: HeaderProps) {
  return (
    <header className="tactical-panel w-full h-12 flex items-center justify-between px-4 z-10 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-slate-900 flex items-center gap-2">🌊 OCEANPULSE</span>
          {!isBackendOffline ? (
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          ) : (
            <span className="text-[11px] font-semibold bg-orange-100 text-orange-700 px-2 py-0.5 rounded uppercase border border-orange-200">Backend Offline - Retrying</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search MMSI..." 
            className="search-input w-[220px] bg-white border border-slate-200 rounded-md pl-9 pr-3 py-1.5 text-sm tabular-nums text-slate-900 outline-none focus:border-[#0056b3] transition-colors"
          />
        </div>
        
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-[11px] uppercase font-bold text-[#0056b3] bg-blue-50 px-2 py-1 rounded border border-blue-100">
            <Lock className="w-3 h-3" /> Admin
          </span>
          <button onClick={onLogout} className="text-sm font-medium text-slate-500 hover:text-red-600 transition">Logout</button>
        </div>
      </div>
    </header>
  );
}
