import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { CaseDetail } from '../api/types';
import { CaseCanvas } from '../components/CaseCanvas';
import { ConfidenceLegend } from '../components/Legend';
import { AppLayout, Breadcrumb } from '../components/Layout';
import { Modal } from '../components/Modal';
import { useToast } from '../components/ToastContext';
import { useObjectUrl } from './hooks';

export function Outcome() {
  const { id } = useParams();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [approveModal, setApproveModal] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showMask, setShowMask] = useState(true);
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.42);
  const navigate = useNavigate();
  const { toast } = useToast();
  const imageUrl = useObjectUrl(id ? `/cases/${id}/image` : undefined);
  const heatmapUrl = useObjectUrl(id ? `/cases/${id}/heatmap` : undefined);
  const maskUrl = useObjectUrl(id ? `/cases/${id}/mask` : undefined);

  useEffect(() => {
    api.get<CaseDetail>(`/cases/${id}`)
      .then(r => setCaseData(r.data))
      .catch(err => setError(err.response?.data?.detail || 'Unable to load outcome.'));
  }, [id]);

  async function finalize() {
    if (!caseData) return;
    setApproveModal(false);
    setBusy(true);
    setError('');
    try {
      await api.post(`/cases/${caseData.id}/finalize`);
      toast('success', 'Case approved successfully.');
      navigate(`/cases/${caseData.id}/export`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Final approval failed.';
      setError(msg);
      toast('error', msg);
    } finally {
      setBusy(false);
    }
  }

  const conf = caseData?.current_result ? Math.round((caseData.current_result.confidence_score ?? 0) * 100) : 0;

  return (
    <AppLayout title="Final Outcome">
      <Breadcrumb items={['Review Dashboard', 'Expert Review', 'Final Outcome']} />
      {error && <div className="inline-error" style={{ marginBottom: 16 }}>{error}</div>}
      {caseData && (
        <>
          {/* Result stat cards */}
          <div className="result-cards">
            {[
              { label: 'Lesions', value: caseData.current_result?.total_lesions ?? 0, sub: 'detected' },
              { label: 'Mask Pixels', value: (caseData.current_result?.total_pixels ?? 0).toLocaleString(), sub: 'segmented' },
              {
                label: caseData.current_result?.source === 'expert' ? 'Confidence' : 'AI Confidence',
                value: caseData.current_result?.source === 'expert' ? 'Expert Verified' : `${conf}%`,
                sub: caseData.current_result?.source === 'expert' ? 'Reviewer approved' : (conf >= 75 ? 'High' : conf >= 50 ? 'Moderate' : 'Low'),
                style: caseData.current_result?.source === 'expert' ? { fontSize: '1.15rem' } : undefined
              },
              { label: 'Resolution', value: `${caseData.width}×${caseData.height}`, sub: `${caseData.file_format} · ${caseData.bit_depth}-bit` },
            ].map(c => (
              <div className="result-card" key={c.label}>
                <div className="result-card-label">{c.label}</div>
                <div className="result-card-value" style={c.style}>{c.value}</div>
                <div className="result-card-sub">{c.sub}</div>
              </div>
            ))}
          </div>

          {/* Confidence bar */}
          <div className="card card-sm" style={{ marginBottom: 20 }}>
            {caseData.current_result?.source === 'expert' ? (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Clinical Confidence</span>
                <span className="badge badge-approved" style={{ fontSize: '0.8125rem' }}>Expert Verified</span>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>AI Confidence</span>
                  <span style={{ fontSize: '0.875rem', fontWeight: 700 }}>{conf}%</span>
                </div>
                <div className="confidence-bar-wrap">
                  <div className="confidence-bar" style={{
                    width: `${conf}%`,
                    background: conf >= 75 ? 'var(--approved)' : conf >= 50 ? 'var(--primary)' : 'var(--pending)',
                  }} />
                </div>
                <ConfidenceLegend />
              </>
            )}
          </div>

          {/* Interactive Case View */}
          <div className="card" style={{ padding: 16, marginBottom: 20 }}>
            <h3 style={{ marginBottom: 12 }}>Interactive Case View</h3>
            <CaseCanvas
              imageUrl={imageUrl}
              heatmapUrl={heatmapUrl}
              maskUrl={maskUrl}
              contours={caseData.current_result?.contour_json}
              showHeatmap={showHeatmap}
              showMask={showMask}
              heatmapOpacity={heatmapOpacity}
              enableZoom
            />
            
            <div style={{ marginTop: 14, background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <button
                  type="button"
                  className={`btn btn-sm ${showHeatmap ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setShowHeatmap(p => !p)}
                  style={{ background: showHeatmap ? 'var(--primary)' : undefined, color: showHeatmap ? '#fff' : undefined }}
                >
                  Heatmap: {showHeatmap ? 'ON' : 'OFF'}
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${showMask ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setShowMask(p => !p)}
                  style={{ background: showMask ? 'var(--primary)' : undefined, color: showMask ? '#fff' : undefined }}
                >
                  Binary Mask: {showMask ? 'ON' : 'OFF'}
                </button>
                <span className="text-xs text-muted">Independent view toggles</span>
              </div>
              
              {showHeatmap && (
                <div className="heatmap-slider-row" style={{ marginBottom: 10 }}>
                  <label>Opacity: <strong>{Math.round(heatmapOpacity * 100)}%</strong></label>
                  <input type="range" min={0} max={100} value={Math.round(heatmapOpacity * 100)}
                    onChange={e => setHeatmapOpacity(Number(e.target.value) / 100)} style={{ flex: 1 }} />
                </div>
              )}
              
              <ConfidenceLegend />
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <Link
              className={`btn btn-ghost ${caseData.is_finalized ? 'disabled' : ''}`}
              to={`/cases/${caseData.id}/reannotate`}
              style={{ pointerEvents: caseData.is_finalized ? 'none' : undefined, opacity: caseData.is_finalized ? 0.5 : 1 }}
            >
              ← Reannotate
            </Link>
            <button
              className="btn btn-primary"
              disabled={busy || caseData.is_finalized}
              onClick={() => setApproveModal(true)}
              id="btn-final-approval"
            >
              {busy ? 'Approving…' : caseData.is_finalized ? '✓ Already Approved' : 'Final Approval'}
            </button>
          </div>
        </>
      )}

      <Modal
        open={approveModal}
        title="Confirm Final Approval"
        message="Approving this case is irreversible. The case will be marked as approved and locked."
        confirmLabel="Approve Case"
        onConfirm={finalize}
        onCancel={() => setApproveModal(false)}
      />
    </AppLayout>
  );
}
