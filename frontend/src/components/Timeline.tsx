import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { formatKST } from '../utils/time';

interface TimelineEvent {
  id: number;
  action: string;
  user_name: string;
  user_role: string;
  timestamp: string;
  details: any;
}

const ACTION_MAP: Record<string, { title: string; emoji: string }> = {
  upload: { title: 'Scan Uploaded', emoji: '📂' },
  run_inference: { title: 'AI Inference Run', emoji: '🤖' },
  submit_for_review: { title: 'Submitted for Review', emoji: '📤' },
  reannotate: { title: 'Re-annotated', emoji: '✍️' },
  finalize: { title: 'Final Approved & Locked', emoji: '🛡️' },
  report_export: { title: 'PDF Report Exported', emoji: '📥' },
};

export function Timeline({ caseId }: { caseId: number }) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<TimelineEvent[]>(`/cases/${caseId}/timeline`)
      .then(r => setEvents(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return <div className="text-xs text-muted" style={{ padding: '10px 0' }}>Loading lifecycle log…</div>;
  }

  if (!events.length) {
    return <div className="text-xs text-faint" style={{ padding: '10px 0' }}>No timeline history available.</div>;
  }

  return (
    <div style={{ marginTop: 14 }}>
      <h3 style={{ fontSize: '0.875rem', marginBottom: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
        📋 Case Lifecycle & Audit Log
      </h3>
      <div className="timeline-container">
        {events.map((event) => {
          const config = ACTION_MAP[event.action] || { title: event.action, emoji: '📝' };
          // Display timestamp in KST
          const kstTime = formatKST(event.timestamp);

          return (
            <div className="timeline-item" key={event.id}>
              <div className={`timeline-badge action-${event.action}`} title={event.action}>
                {config.emoji}
              </div>
              <div className="timeline-content">
                <span className="timeline-action-title">{config.title}</span>
                <span className="timeline-meta">
                  by {event.user_name} ({event.user_role === 'expert_reviewer' ? 'Expert Reviewer' : 'Sonologist'}) · {kstTime}
                </span>
                {event.details && (
                  <span className="timeline-details">{JSON.stringify(event.details)}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
