import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, Area, AreaChart, ComposedChart
} from 'recharts';
import { getSupply, getSupplyScenarios } from '../services/api';

type Scenario = 'current_trajectory' | 'top1_target' | 'top5_targets' | 'exploration_acceleration';

const SCENARIO_LABELS: Record<Scenario, string> = {
  current_trajectory: 'Current trajectory',
  top1_target: 'Add top 1 target',
  top5_targets: 'Add top 5 targets',
  exploration_acceleration: 'Exploration acceleration',
};

const SCENARIO_COLORS: Record<Scenario, string> = {
  current_trajectory: '#697078',
  top1_target: '#B45309',
  top5_targets: '#40916C',
  exploration_acceleration: '#1D4E89',
};

export default function SupplyIntelligence() {
  const [histData, setHistData] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any>(null);
  const [selectedScenario, setSelectedScenario] = useState<Scenario>('current_trajectory');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getSupply(), getSupplyScenarios()])
      .then(([h, s]) => { setHistData(h); setScenarios(s); setLoading(false); })
      .catch(() => { setLoading(false); });
  }, []);

  if (loading) return <div style={{ padding: 32, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)' }}><span className="spinner" />Loading supply data…</div>;

  // Build historical chart data
  const histChart = histData ? histData.years.map((yr: number, i: number) => ({
    year: yr,
    'India Production': histData.india_production[i],
    'India Demand': histData.india_demand[i],
    'Shortfall': +(histData.india_demand[i] - histData.india_production[i]).toFixed(2),
  })) : [];

  // Build forecast comparison data
  const sc = scenarios?.scenarios;
  const forecastChart = sc ? scenarios.years.map((yr: number, i: number) => ({
    year: yr,
    demand: sc.current_trajectory.demand[i],
    ...(Object.fromEntries(
      Object.entries(sc).map(([k, v]: [string, any]) => [k, v.supply[i]])
    )),
  })) : [];

  const activeScenario = sc?.[selectedScenario];

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <div className="page">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Manganese Supply Outlook</h1>
            <p className="page-subtitle">India production vs. demand — Exploration scenario analysis</p>
          </div>
          <div className="demo-banner">
            <span>⚠</span>
            Scenario estimates for decision support. Not certified production forecasts.
          </div>
        </div>

        {/* Key stats */}
        <div className="stats-row">
          {[
            { label: 'India Production 2025', val: '3.62 Mt', sub: 'Estimated' },
            { label: 'India Demand 2025', val: '5.68 Mt', sub: 'Projected' },
            { label: 'Supply Gap 2025', val: '2.06 Mt', sub: 'Shortfall', color: 'var(--red-light)' },
            { label: 'Gap 2030 (Base)', val: `${scenarios?.base_gap_2030 || '3.50'} Mt`, sub: 'Current trajectory', color: 'var(--amber)' },
          ].map(s => (
            <div key={s.label} className="stat-box">
              <div className="stat-label">{s.label}</div>
              <div className="stat-value" style={{ color: s.color || 'var(--text-primary)' }}>{s.val}</div>
              <div className="stat-sub">{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Historical chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">India: Historical Production vs Demand (Mt)</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>2015–2025</span>
          </div>
          <div className="card-body" style={{ padding: '16px 16px 8px' }}>
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={histChart} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E7E8EA" />
                <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#697078' }} />
                <YAxis tick={{ fontSize: 11, fill: '#697078' }} unit=" Mt" domain={[0, 8]} />
                <Tooltip
                  contentStyle={{ fontSize: 11, border: '1px solid var(--border)', borderRadius: 4 }}
                  formatter={(v: any, n: any) => [`${v} Mt`, n] as any}
                />
                <ReferenceLine y={0} stroke="var(--border)" />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="India Demand" stroke="#B45309" fill="#FEF3C7" fillOpacity={0.4} strokeWidth={2} />
                <Line type="monotone" dataKey="India Production" stroke="#2D6A4F" strokeWidth={2.5} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Scenario selector + forecast */}
        {sc && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">Supply Forecast by Scenario (Mt)</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>2026–2030</span>
              </div>
              <div className="card-body" style={{ padding: '16px 16px 8px' }}>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={forecastChart} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E7E8EA" />
                    <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#697078' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#697078' }} unit=" Mt" domain={[3, 8]} />
                    <Tooltip contentStyle={{ fontSize: 11, border: '1px solid var(--border)', borderRadius: 4 }}
                      formatter={(v: any, n: any) => [`${v} Mt`, String(n)]} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line dataKey="demand" stroke="#DC2626" strokeWidth={2} strokeDasharray="5 3" dot={false} name="Demand" />
                    {(Object.keys(SCENARIO_LABELS) as Scenario[]).map(sk => (
                      <Line key={sk} dataKey={sk}
                        stroke={SCENARIO_COLORS[sk]}
                        strokeWidth={selectedScenario === sk ? 2.5 : 1}
                        strokeOpacity={selectedScenario === sk ? 1 : 0.35}
                        dot={false}
                        name={SCENARIO_LABELS[sk]}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Scenario panel */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="card">
                <div className="card-header"><span className="card-title">Scenario</span></div>
                <div style={{ padding: '8px 0' }}>
                  {(Object.keys(SCENARIO_LABELS) as Scenario[]).map(sk => (
                    <label key={sk} style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '7px 14px', cursor: 'pointer',
                      background: selectedScenario === sk ? 'var(--bg-secondary)' : 'transparent',
                    }}>
                      <input type="radio" name="scenario" checked={selectedScenario === sk}
                        onChange={() => setSelectedScenario(sk)}
                        style={{ accentColor: SCENARIO_COLORS[sk] }} />
                      <span style={{ fontSize: 12, color: selectedScenario === sk ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: selectedScenario === sk ? 600 : 400 }}>
                        {SCENARIO_LABELS[sk]}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {activeScenario && (
                <div className="card">
                  <div className="card-header"><span className="card-title">Projected Gap 2030</span></div>
                  <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div className="metric-item">
                      <div className="metric-label">Supply Gap</div>
                      <div className="metric-value" style={{ color: activeScenario.gap_2030 < scenarios.base_gap_2030 ? 'var(--green)' : 'var(--red-light)', fontSize: 22 }}>
                        {activeScenario.gap_2030} Mt
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Gap Reduction</div>
                      <div className="metric-value" style={{ color: 'var(--green)', fontSize: 18 }}>
                        {Math.round((1 - activeScenario.gap_2030 / scenarios.base_gap_2030) * 100)}%
                      </div>
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.4 }}>
                      Scenario estimate. Not a certified production forecast.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="demo-banner">
          <span>ℹ</span>
          "Every field result becomes new evidence for the next exploration decision." — MANGANAI Closed-Loop System
        </div>
      </div>
    </div>
  );
}
