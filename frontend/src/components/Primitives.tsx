import { useEffect, useState } from "react";
import { ApiError } from "../api/client";

export function usePageTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} | Biblioteca`;
    return () => {
      document.title = "Biblioteca";
    };
  }, [title]);
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  return <button className={`button button--${variant} ${className}`} {...props} />;
}

export function FieldError({ children }: { children?: string }) {
  return children ? <span className="field-error" role="alert">{children}</span> : null;
}

export function RequestError({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof ApiError ? error.message : "No pudimos cargar esta información.";
  return (
    <div className="notice notice--error" role="alert">
      <span className="notice__icon" aria-hidden="true">!</span>
      <div>
        <p>{message}</p>
        {retry && <button className="text-button" type="button" onClick={retry}>Intentar de nuevo</button>}
      </div>
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><h2>{title}</h2><p>{text}</p></div>;
}

export function Skeletons({ count = 4 }: { count?: number }) {
  return (
    <div className="skeleton-grid" aria-label="Cargando" role="status">
      {Array.from({ length: count }, (_, index) => <div className="skeleton-card" key={index}><div /><span /><span /></div>)}
    </div>
  );
}

export function useAsyncAction<T extends unknown[]>(
  action: (...args: T) => Promise<void>,
): { run: (...args: T) => Promise<void>; busy: boolean } {
  const [busy, setBusy] = useState(false);
  const run = async (...args: T) => {
    if (busy) return;
    setBusy(true);
    try {
      await action(...args);
    } finally {
      setBusy(false);
    }
  };
  return { run, busy };
}

export function confirmDelete(message: string): boolean {
  return window.confirm(message);
}
