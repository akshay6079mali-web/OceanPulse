import React, { useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../App';

interface LoginModalProps {
  onLogin: (token: string) => void;
}

export default function LoginModal({ onLogin }: LoginModalProps) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      const res = await axios.post(`${API_BASE_URL}/token`, formData, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
      onLogin(res.data.access_token);
    } catch (err: any) {
      if (err.response?.status === 401) {
        setError('Invalid username or password');
      } else if (err.code === 'ERR_NETWORK' || !err.response) {
        setError('Backend server is offline. Run RUN_OCEANPULSE.bat first.');
      } else {
        setError(`Login failed: ${err.response?.data?.detail || 'Unknown error'}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
      <div className="w-full max-w-sm p-6 bg-white border border-slate-200 rounded-lg shadow-2xl">
        <div className="flex items-center gap-2 mb-6">
          <span className="text-2xl font-bold text-[#0056b3]">OCEANPULSE</span>
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
        </div>
        <p className="text-xs text-slate-500 uppercase tracking-widest mb-4">Secure Authentication Required</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-slate-600 text-xs font-semibold uppercase mb-1">Username</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full bg-white border border-slate-200 p-2.5 text-slate-900 rounded focus:outline-none focus:border-[#0056b3] transition-colors" />
          </div>
          <div>
            <label className="block text-slate-600 text-xs font-semibold uppercase mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-white border border-slate-200 p-2.5 text-slate-900 rounded focus:outline-none focus:border-[#0056b3] transition-colors" />
          </div>
          {error && <div className="text-red-600 text-sm bg-red-50 border border-red-100 p-2 rounded">{error}</div>}
          <button type="submit" disabled={isLoading} className={`w-full ${isLoading ? 'bg-blue-300 cursor-not-allowed' : 'bg-[#0056b3] hover:bg-blue-800'} text-white font-bold text-sm uppercase tracking-wider p-2.5 rounded transition-colors`}>
            {isLoading ? 'Authenticating...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
}
