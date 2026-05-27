import { createContext, useCallback, useContext, useEffect, useRef, useState, ReactNode } from 'react';

export type ToastType = 'success' | 'error' | 'info';
interface ToastItem { id: number; type: ToastType; message: string; }
interface ToastCtx { toast: (type: ToastType, message: string) => void; }

const Ctx = createContext<ToastCtx | null>(null);

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

function ToastBanner({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    timerRef.current = setTimeout(onClose, 4000);
    return () => clearTimeout(timerRef.current);
  }, [onClose]);

  const icons: Record<ToastType, string> = {
    success: '✓',
    error: '✕',
    info: 'ℹ',
  };

  return (
    <div className={`toast toast-${item.type}`} role="alert" aria-live="polite">
      <span className="toast-icon">{icons[item.type]}</span>
      <span className="toast-message">{item.message}</span>
      <button className="toast-close" onClick={onClose} aria-label="Dismiss">✕</button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback((type: ToastType, message: string) => {
    const id = Date.now();
    setToasts(prev => [...prev.slice(-4), { id, type, message }]);
  }, []);

  const remove = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <Ctx.Provider value={{ toast }}>
      {children}
      <div className="toast-stack" aria-label="Notifications">
        {toasts.map(t => (
          <ToastBanner key={t.id} item={t} onClose={() => remove(t.id)} />
        ))}
      </div>
    </Ctx.Provider>
  );
}
