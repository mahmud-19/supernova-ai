import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { CaseDetail } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { AppLayout } from '../components/Layout';
import { SkeletonTable } from '../components/Skeleton';

export function Analytics() {
  const { user } = useAuth();
  const [cases, setCases] = useState<CaseDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [timeframe, setTimeframe] = useState<'7d' | '30d' | 'all'>('all');
  const [genderFilter, setGenderFilter] = useState<string>('all');

  useEffect(() => {
    const endpoint = user?.role === 'sonologist' ? '/cases/mine' : '/cases';
    api.get<CaseDetail[]>(endpoint)
      .then(r => setCases(r.data))
      .catch(err => setError(err.response?.data?.detail || 'Unable to fetch analytics data.'))
      .finally(() => setLoading(false));
  }, [user]);

  // Apply filters
  const filteredCases = useMemo(() => {
    return cases.filter(c => {
      // 1. Timeframe
      if (timeframe !== 'all') {
        const date = c.exam_date ? new Date(c.exam_date) : new Date(c.created_at);
        const diffDays = (new Date().getTime() - date.getTime()) / (1000 * 3600 * 24);
        if (timeframe === '7d' && diffDays > 7) return false;
        if (timeframe === '30d' && diffDays > 30) return false;
      }
      // 2. Gender
      if (genderFilter !== 'all' && c.gender !== genderFilter) {
        return false;
      }
      return true;
    });
  }, [cases, timeframe, genderFilter]);

  // KPIs
  const totalCases = filteredCases.length;
  const pendingCount = filteredCases.filter(c => c.status === 'pending').length;
  const inReviewCount = filteredCases.filter(c => c.status === 'in_review').length;
  const approvedCount = filteredCases.filter(c => c.status === 'approved').length;
  
  const avgConf = useMemo(() => {
    const valid = filteredCases.filter(c => c.current_result?.confidence_score !== undefined && c.current_result?.source !== 'expert');
    if (!valid.length) return 0;
    return Math.round((valid.reduce((sum, c) => sum + (c.current_result?.confidence_score ?? 0), 0) / valid.length) * 100);
  }, [filteredCases]);

  const avgPixels = useMemo(() => {
    const valid = filteredCases.filter(c => c.current_result?.total_pixels !== undefined);
    if (!valid.length) return 0;
    return Math.round(valid.reduce((sum, c) => sum + (c.current_result?.total_pixels ?? 0), 0) / valid.length);
  }, [filteredCases]);

  // Chart 1: Volume by Day of Week (SVG Bar Chart)
  const volumeData = useMemo(() => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const counts = [0, 0, 0, 0, 0, 0, 0];
    filteredCases.forEach(c => {
      const date = c.exam_date ? new Date(c.exam_date) : new Date(c.created_at);
      counts[date.getDay()] += 1;
    });
    const maxVal = Math.max(...counts, 4); // fallback minimum max of 4 for clean scaling
    return days.map((day, idx) => ({
      label: day,
      value: counts[idx],
      percent: (counts[idx] / maxVal) * 100
    }));
  }, [filteredCases]);

  // Chart 2: AI Confidence Distribution (SVG Area Chart)
  const confidenceDistribution = useMemo(() => {
    const buckets = ['<40%', '40-59%', '60-74%', '75-89%', '90%+'];
    const counts = [0, 0, 0, 0, 0];
    
    filteredCases.forEach(c => {
      const score = c.current_result?.confidence_score;
      if (score === undefined || c.current_result?.source === 'expert') return;
      const pct = score * 100;
      if (pct < 40) counts[0]++;
      else if (pct < 60) counts[1]++;
      else if (pct < 75) counts[2]++;
      else if (pct < 90) counts[3]++;
      else counts[4]++;
    });

    const maxVal = Math.max(...counts, 2);
    // Convert to points for SVG area/line chart
    // Area dimensions: width = 400, height = 150
    // x spacing: 400 / 4 = 100
    const points = buckets.map((bucket, idx) => {
      const x = 40 + idx * 80;
      const y = 140 - (counts[idx] / maxVal) * 100;
      return { x, y, label: bucket, val: counts[idx] };
    });

    return { points, maxVal };
  }, [filteredCases]);

  // Chart 3: Lesion Count Frequency Breakdown (SVG Donut Chart)
  const lesionBreakdown = useMemo(() => {
    let zero = 0, one = 0, two = 0, threePlus = 0;
    filteredCases.forEach(c => {
      const count = c.current_result?.total_lesions;
      if (count === undefined || count === 0) zero++;
      else if (count === 1) one++;
      else if (count === 2) two++;
      else threePlus++;
    });

    const total = zero + one + two + threePlus;
    if (total === 0) return [];
    
    const items = [
      { label: '0 Lesions', count: zero, color: 'var(--text-faint)' },
      { label: '1 Lesion', count: one, color: 'var(--primary)' },
      { label: '2 Lesions', count: two, color: 'var(--in-review)' },
      { label: '3+ Lesions', count: threePlus, color: 'var(--pending)' },
    ].filter(i => i.count > 0);

    let accum = 0;
    return items.map(item => {
      const pct = (item.count / total) * 100;
      const offset = accum;
      accum += pct;
      return { ...item, pct: Math.round(pct), offset: (offset / 100) * 314.16 }; // circumference = 2 * PI * r (r = 50 -> 314.16)
    });
  }, [filteredCases]);

  return (
    <AppLayout title="Clinical Analytics">
      {loading ? (
        <div style={{ padding: 24 }}><SkeletonTable rows={8} cols={4} /></div>
      ) : error ? (
        <div className="inline-error" style={{ margin: 20 }}>{error}</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Header Toolbar */}
          <div className="card card-tight" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', marginBottom: 2 }}>System Performance & Analytics</h2>
              <p className="text-xs">Dynamic visual audit summaries of ultrasound triage files.</p>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <select
                className="filter-select"
                value={timeframe}
                onChange={e => setTimeframe(e.target.value as any)}
                aria-label="Select timeframe"
                style={{ width: 140 }}
              >
                <option value="all">All Time</option>
                <option value="30d">Last 30 Days</option>
                <option value="7d">Last 7 Days</option>
              </select>
              <select
                className="filter-select"
                value={genderFilter}
                onChange={e => setGenderFilter(e.target.value)}
                aria-label="Filter by gender"
                style={{ width: 140 }}
              >
                <option value="all">All Genders</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          {/* KPI Widget Cards */}
          <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', marginBottom: 0 }}>
            {[
              { label: 'Total Scans', value: totalCases, sub: `${approvedCount} Approved` },
              { label: 'In Review', value: inReviewCount, sub: `${pendingCount} Pending`, cls: 'in-review-val' },
              { label: 'Avg AI Confidence', value: `${avgConf}%`, sub: 'Active overlay mean' },
              { label: 'Mean Lesion Size', value: `${avgPixels.toLocaleString()} px`, sub: 'Segmented pixel density' },
              { label: 'Approved Ratio', value: totalCases > 0 ? `${Math.round((approvedCount / totalCases) * 100)}%` : '0%', sub: 'Audit finalized status' }
            ].map((kpi, i) => (
              <div className="stat-card" key={i}>
                <span className="stat-label">{kpi.label}</span>
                <strong className={`stat-value ${kpi.cls || ''}`} style={{ fontSize: '1.5rem', margin: '4px 0' }}>{kpi.value}</strong>
                <span className="text-xs text-muted" style={{ fontWeight: 500 }}>{kpi.sub}</span>
              </div>
            ))}
          </div>

          {/* Charts Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {/* Chart 1: Case Volume */}
            <div className="chart-container">
              <h3 style={{ marginBottom: 12, fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                📊 Upload Volume by Day of Week
              </h3>
              {totalCases === 0 ? (
                <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-faint)' }}>
                  No case data to render chart.
                </div>
              ) : (
                <svg width="100%" height="180" viewBox="0 0 450 180">
                  {/* Grid Lines */}
                  {[0, 25, 50, 75, 100].map(h => (
                    <line key={h} x1="30" y1={20 + h} x2="430" y2={20 + h} className="chart-grid" />
                  ))}
                  {/* Bars */}
                  {volumeData.map((bar, idx) => {
                    const x = 45 + idx * 56;
                    const height = (bar.percent / 100) * 100;
                    const y = 120 - height;
                    return (
                      <g key={bar.label}>
                        <rect
                          x={x}
                          y={y}
                          width="24"
                          height={height}
                          rx="4"
                          className="chart-bar"
                        />
                        {/* Text Value */}
                        <text x={x + 12} y={y - 6} textAnchor="middle" style={{ fontSize: 10, fontWeight: 700, fill: 'var(--text-muted)' }}>
                          {bar.value > 0 ? bar.value : ''}
                        </text>
                        {/* Label */}
                        <text x={x + 12} y="136" textAnchor="middle" className="chart-axis-text">
                          {bar.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>

            {/* Chart 2: AI Confidence Distribution */}
            <div className="chart-container">
              <h3 style={{ marginBottom: 12, fontSize: '1rem' }}>
                📈 AI Confidence Bracket Distribution
              </h3>
              {totalCases === 0 ? (
                <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-faint)' }}>
                  No case data to render chart.
                </div>
              ) : (
                <svg width="100%" height="180" viewBox="0 0 420 180">
                  {/* Grid Lines */}
                  {[0, 25, 50, 75, 100].map(h => (
                    <line key={h} x1="40" y1={40 + h} x2="360" y2={40 + h} className="chart-grid" />
                  ))}
                  
                  {/* Area Path */}
                  <path
                    d={`
                      M ${confidenceDistribution.points[0].x} 140
                      ${confidenceDistribution.points.map(p => `L ${p.x} ${p.y}`).join(' ')}
                      L ${confidenceDistribution.points[confidenceDistribution.points.length - 1].x} 140
                      Z
                    `}
                    className="chart-area"
                  />

                  {/* Line Path */}
                  <path
                    d={confidenceDistribution.points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')}
                    className="chart-line"
                  />

                  {/* Points & Labels */}
                  {confidenceDistribution.points.map((p, idx) => (
                    <g key={idx}>
                      <circle cx={p.x} cy={p.y} r="5" fill="var(--primary)" stroke="var(--white)" strokeWidth="2" />
                      {/* Tooltip Count */}
                      <text x={p.x} y={p.y - 8} textAnchor="middle" style={{ fontSize: 9, fontWeight: 700, fill: 'var(--text-muted)' }}>
                        {p.val}
                      </text>
                      {/* X Axis Label */}
                      <text x={p.x} y="156" textAnchor="middle" className="chart-axis-text">
                        {p.label}
                      </text>
                    </g>
                  ))}
                </svg>
              )}
            </div>

            {/* Chart 3: Lesion Count Frequency breakdown */}
            <div className="chart-container" style={{ gridColumn: 'span 2' }}>
              <h3 style={{ marginBottom: 16, fontSize: '1rem' }}>
                🎯 Lesion Frequency Distribution (Approved & Active Scans)
              </h3>
              {totalCases === 0 ? (
                <div style={{ height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-faint)' }}>
                  No case data to render breakdown.
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 60, flexWrap: 'wrap' }}>
                  {/* Donut SVG */}
                  <svg width="150" height="150" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" strokeWidth="8" />
                    {lesionBreakdown.map((segment, idx) => (
                      <circle
                        key={idx}
                        cx="60"
                        cy="60"
                        r="50"
                        fill="none"
                        stroke={segment.color}
                        strokeWidth="10"
                        strokeDasharray={`${(segment.pct / 100) * 314.16} 314.16`}
                        strokeDashoffset={-segment.offset}
                        transform="rotate(-90 60 60)"
                        strokeLinecap="round"
                        className="chart-donut-segment"
                      />
                    ))}
                    {/* Centered Total */}
                    <text x="60" y="58" textAnchor="middle" style={{ fontSize: 16, fontWeight: 800, fill: 'var(--text)' }}>
                      {totalCases}
                    </text>
                    <text x="60" y="74" textAnchor="middle" style={{ fontSize: 9, fontWeight: 600, fill: 'var(--text-muted)' }}>
                      Total Scans
                    </text>
                  </svg>

                  {/* Donut Legend */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 200 }}>
                    {lesionBreakdown.map((segment, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', justifySelf: 'stretch', justifyContent: 'space-between', gap: 14 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 12, height: 12, borderRadius: 3, background: segment.color }} />
                          <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{segment.label}</span>
                        </div>
                        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                          <strong>{segment.count}</strong> ({segment.pct}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
