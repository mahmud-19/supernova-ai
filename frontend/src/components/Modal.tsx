import { useEffect, useRef, ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
}

export function Modal({ open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = false, onConfirm, onCancel, children }: ModalProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) confirmRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onCancel();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-card">
        <h2 className="modal-title" id="modal-title">{title}</h2>
        {message && <p className="modal-message">{message}</p>}
        {children}
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onCancel}>{cancelLabel}</button>
          <button
            ref={confirmRef}
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
