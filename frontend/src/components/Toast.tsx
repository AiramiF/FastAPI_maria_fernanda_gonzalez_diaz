import { createContext, useCallback, useContext, useMemo, useState } from "react";

type ToastKind = "success" | "error";
interface ToastMessage {
  id: number;
  kind: ToastKind;
  message: string;
}
interface ToastValue {
  show: (kind: ToastKind, message: string) => void;
}

const ToastContext = createContext<ToastValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const show = useCallback((kind: ToastKind, message: string) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, kind, message }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 5000);
  }, []);
  const value = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div className={`toast toast--${toast.kind}`} key={toast.id} role="status">
            <span className="toast__icon" aria-hidden="true">{toast.kind === "success" ? "✓" : "!"}</span>
            <p>{toast.message}</p>
            <button
              className="icon-button toast__close"
              type="button"
              aria-label="Cerrar aviso"
              onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast debe usarse dentro de ToastProvider");
  return context;
}
