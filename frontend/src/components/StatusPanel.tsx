import { CaseDetail } from '../api/types';

function statusLabel(status: string): string {
  if (status === 'in_review') return 'In Review';
  if (status === 'approved') return 'Approved';
  return 'Pending';
}

export function StatusPanel({ caseData }: { caseData: Pick<CaseDetail, 'status' | 'file_format' | 'width' | 'height' | 'bit_depth' | 'contrast_adjusted'> }) {
  return (
    <aside className="status-panel">
      <h3>Status</h3>
      <span className={`status-badge ${caseData.status === 'approved' ? 'approved' : caseData.status === 'in_review' ? 'in-review' : 'pending'}`}>
        {statusLabel(caseData.status)}
      </span>
      <p style={{ marginTop: 10 }}>{caseData.file_format} | {caseData.width}×{caseData.height}px | {caseData.bit_depth}-bit grayscale | {caseData.contrast_adjusted ? 'contrast adjusted' : 'standard contrast'}</p>
    </aside>
  );
}
