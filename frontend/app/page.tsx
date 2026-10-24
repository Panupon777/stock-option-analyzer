'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import AnalysisDetails from '@/components/AnalysisDetails';

export default function Home() {
  const [ticker, setTicker] = useState('');
  const [market, setMarket] = useState('US');
  const [horizon, setHorizon] = useState('weekly');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const initialTicker = new URLSearchParams(window.location.search).get('ticker');
    if (initialTicker) setTicker(initialTicker.toUpperCase());
    const t = localStorage.getItem('token');
    setToken(t);
  }, []);

  const runAnalysis = async () => {
    if (!token) {
      alert('Please login first');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/analyze', {
        ticker: ticker.toUpperCase(),
        market,
        horizon,
      });
      setResult(response.data);
    } catch (error: any) {
      alert('Error: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-6">
      {/* Input Card */}
      <div className="card">
        <div className="flex flex-wrap gap-3 mb-4">
          <input
            type="text"
            placeholder="Stock ticker, e.g. NVDA, IONQ"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="input-field flex-1 min-w-[150px]"
          />
          <select value={market} onChange={(e) => setMarket(e.target.value)} className="input-field min-w-[120px]">
            <option value="US">🇺🇸 US Market</option>
            <option value="TH">🇹🇭 SET</option>
          </select>
          <select value={horizon} onChange={(e) => setHorizon(e.target.value)} className="input-field min-w-[140px]">
            <option value="weekly">📅 Weekly</option>
            <option value="month1">📆 1 month</option>
            <option value="month2">📆 2 months</option>
            <option value="month3">📆 3 months</option>
          </select>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="btn btn-primary px-6 disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Analyze ↗'}
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="mt-6">
        {result ? (
          <div className="space-y-4">
            {/* Stock Metrics */}
            <div className="grid grid-cols-4 gap-3">
              <div className="card">
                <div className="text-xs text-muted mb-1">Direction</div>
                <div className="text-2xl font-bold">
                  {result.direction === 'BULLISH' ? '🟢' : result.direction === 'BEARISH' ? '🔴' : '⚪'}
                </div>
                <div className="text-xs text-muted mt-1">{result.confidence}% confidence</div>
              </div>

              <div className="card">
                <div className="text-xs text-muted mb-1">Current price</div>
                <div className="text-xl font-bold">${result.currentPrice?.toFixed(2)}</div>
              </div>

              <div className="card">
                <div className="text-xs text-muted mb-1">Target price</div>
                <div className="text-xl font-bold">${result.priceTarget?.toFixed(2)}</div>
              </div>

              <div className="card">
                <div className="text-xs text-muted mb-1">Options</div>
                <div className="text-lg font-bold">{result.optionStrategy?.recommended}</div>
              </div>
            </div>

            {/* Call/Put Explanations */}
            <div className="grid grid-cols-2 gap-4">
              <div className="card bg-gradient-to-br from-green-900/20 to-emerald-900/10 border-green-700/30">
                <div className="text-lg font-bold text-green-400 mb-2">🟢 Trade CALL</div>
                <p className="text-sm text-white/80">{result.callExplanation}</p>
              </div>
              <div className="card bg-gradient-to-br from-red-900/20 to-rose-900/10 border-red-700/30">
                <div className="text-lg font-bold text-red-400 mb-2">🔴 Trade PUT</div>
                <p className="text-sm text-white/80">{result.putExplanation}</p>
              </div>
            </div>

            {/* Summary */}
            <div className="card bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-purple-700/30">
              <div className="font-bold mb-2">{result.direction} — {result.summaryTH}</div>
            </div>

            {/* News */}
            {result.stock_data?.news?.length > 0 && (
              <div className="card">
                <div className="font-bold mb-3">📰 Latest news (Finnhub)</div>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {result.stock_data.news.slice(0, 5).map((n: any, i: number) => (
                    <div key={i} className="border-t border-border pt-2 text-sm">
                      <div className="font-semibold">{n.title}</div>
                      <div className="text-xs text-muted mt-1">
                        {n.published_label} • {n.publisher}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <AnalysisDetails key={JSON.stringify(result)} result={result} />
            {/* Model Used */}
            <div className="text-xs text-muted text-center">
              {result.model_used} • {result.stock_data?.fetched_at_label}
            </div>
          </div>
        ) : (
          <div className="card text-center py-12 text-muted">
            <div className="text-4xl mb-4">◎</div>
            <div>Log in, enter a stock ticker, and click "Analyze"</div>
            <div className="text-xs mt-2">AI analysis with real-time Finnhub news + probability of reaching the strike price</div>
          </div>
        )}
      </div>
    </div>
  );
}


