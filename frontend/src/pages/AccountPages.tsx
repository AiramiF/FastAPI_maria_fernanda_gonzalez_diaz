import { useEffect, useState } from "react";
import { api, queryString } from "../api/client";
import type { Loan, Member, Page } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Button, EmptyState, FieldError, RequestError, Skeletons, usePageTitle } from "../components/Primitives";
import { useToast } from "../components/Toast";

export function ProfilePage() {
  usePageTitle("Mi perfil");
  const { user, reloadUser } = useAuth();
  const toast = useToast();
  const [member, setMember] = useState<Member | null>(null);
  const [name, setName] = useState(user?.nombre ?? "");
  const [phone, setPhone] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profileError, setProfileError] = useState<unknown>(null);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [passwordError, setPasswordError] = useState("");
  const [passwordFieldError, setPasswordFieldError] = useState("");
  const [loading, setLoading] = useState(user?.rol === "socio");
  const [busyProfile, setBusyProfile] = useState(false);
  const [busyPassword, setBusyPassword] = useState(false);

  useEffect(() => {
    if (user?.rol !== "socio") return;
    let active = true;
    void api<Member>("/socios/me").then((result) => {
      if (!active) return;
      setMember(result);
      setName(result.nombre);
      setPhone(result.telefono ?? "");
    }).catch((reason: unknown) => {
      if (active) setProfileError(reason);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [user?.rol]);

  const saveProfile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusyProfile(true);
    setSaveError(null);
    try {
      const saved = await api<Member>("/socios/me", {
        method: "PATCH",
        body: JSON.stringify({ nombre: name.trim(), ...(phone.trim() ? { telefono: phone.trim() } : {}) }),
      });
      setMember(saved);
      await reloadUser();
      toast.show("success", "Tus datos se actualizaron.");
    } catch (error) {
      setSaveError(error);
    } finally {
      setBusyProfile(false);
    }
  };

  const changePassword = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordError("");
    setPasswordFieldError("");
    if (newPassword.length < 8 || newPassword.length > 64 || !/[A-Z]/.test(newPassword) || !/[a-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      setPasswordFieldError("Usa entre 8 y 64 caracteres, con mayúscula, minúscula y número.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordFieldError("Las contraseñas no coinciden.");
      return;
    }
    setBusyPassword(true);
    try {
      await api<void>("/auth/me/password", {
        method: "PATCH",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword, confirm_password: confirmPassword }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.show("success", "Tu contraseña se actualizó.");
    } catch (error) {
      setPasswordError(error instanceof Error ? error.message : "No se pudo actualizar la contraseña.");
    } finally {
      setBusyPassword(false);
    }
  };

  return (
    <section className="container page-section narrow-section">
      <p className="eyebrow eyebrow--light">Tu espacio</p>
      <h1>Mi perfil</h1>
      <p className="page-lead">Hola, {user?.nombre}. Aquí puedes gestionar tu cuenta.</p>
      {user?.rol === "socio" ? (
        <section className="panel-card">
          <h2>Datos personales</h2>
          {loading && <Skeletons count={1} />}
          {!loading && profileError !== null && <RequestError error={profileError} retry={() => window.location.reload()} />}
          {!loading && !profileError && member && (
            <form className="form-stack" onSubmit={saveProfile}>
              {saveError !== null && <RequestError error={saveError} />}
              <label className="field">Nombre completo<input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} required minLength={3} /></label>
              <label className="field">Correo electrónico<input value={member.email} readOnly aria-describedby="email-note" /><span id="email-note" className="field-note">El correo no se puede cambiar desde aquí.</span></label>
              <label className="field">Teléfono<input type="tel" autoComplete="tel" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
              <Button type="submit" disabled={busyProfile}>{busyProfile ? "Guardando…" : "Guardar cambios"}</Button>
            </form>
          )}
        </section>
      ) : (
        <section className="panel-card">
          <h2>Datos de la cuenta</h2>
          <dl className="account-facts">
            <div><dt>Nombre</dt><dd>{user?.nombre}</dd></div>
            <div><dt>Correo</dt><dd>{user?.email}</dd></div>
            <div><dt>Rol</dt><dd>{roleName(user?.rol)}</dd></div>
          </dl>
        </section>
      )}
      <section className="panel-card">
        <h2>Cambiar contraseña</h2>
        {passwordError && <div className="notice notice--error" role="alert"><span className="notice__icon" aria-hidden="true">!</span><p>{passwordError}</p></div>}
        <form className="form-stack" onSubmit={changePassword}>
          <label className="field">Contraseña actual<input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          <label className="field">Nueva contraseña<input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /><FieldError>{passwordFieldError}</FieldError></label>
          <label className="field">Confirmar contraseña<input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></label>
          <Button type="submit" disabled={busyPassword}>{busyPassword ? "Actualizando…" : "Actualizar contraseña"}</Button>
        </form>
      </section>
    </section>
  );
}

export function MemberLoansPage({ finesOnly = false }: { finesOnly?: boolean }) {
  const title = finesOnly ? "Mis multas" : "Mis préstamos";
  usePageTitle(title);
  const [state, setState] = useState("");
  const [page, setPage] = useState<Page<Loan> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [skip, setSkip] = useState(0);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const path = finesOnly
      ? `/socios/me/multas${queryString({ skip, limit: 20 })}`
      : `/socios/me/prestamos${queryString({ skip, limit: 20, estado: state || undefined })}`;
    void api<Page<Loan>>(path).then((result) => {
      if (active) setPage(result);
    }).catch((reason: unknown) => {
      if (active) setError(reason);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [finesOnly, skip, state, reloadKey]);

  return (
    <section className="container page-section">
      <p className="eyebrow eyebrow--light">Tu actividad</p>
      <h1>{title}</h1>
      {!finesOnly && <label className="compact-filter">Estado
        <select value={state} onChange={(event) => { setState(event.target.value); setSkip(0); }}>
          <option value="">Todos</option><option value="activo">Activo</option><option value="vencido">Vencido</option><option value="devuelto">Devuelto</option>
        </select>
      </label>}
      {loading && <Skeletons />}
      {!loading && error !== null && <RequestError error={error} retry={() => setReloadKey((key) => key + 1)} />}
      {!loading && !error && page?.items.length === 0 && <EmptyState title={finesOnly ? "No tienes multas pendientes" : "Aún no tienes préstamos"} text={finesOnly ? "Disfruta de tus lecturas sin preocupaciones." : "Cuando tengas un préstamo, aparecerá aquí."} />}
      {!loading && !error && page && page.items.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Libro</th><th>Préstamo</th><th>Fecha límite</th><th>Estado</th>{finesOnly && <th>Multa</th>}</tr></thead>
              <tbody>{page.items.map((loan) => (
                <tr key={loan.id}>
                  <td>{loan.libro.titulo}</td><td>{formatDate(loan.fecha_prestamo)}</td><td>{formatDate(loan.fecha_limite)}</td>
                  <td><span className={`status-badge status-badge--${loan.estado}`}>{stateName(loan.estado)}</span></td>
                  {finesOnly && <td>{formatMoney(loan.multa)}</td>}
                </tr>
              ))}</tbody>
            </table>
          </div>
          <Pager skip={skip} total={page.total} onChange={setSkip} />
        </>
      )}
    </section>
  );
}

function Pager({ skip, total, onChange }: { skip: number; total: number; onChange: (skip: number) => void }) {
  const limit = 20;
  return (
    <nav className="pagination" aria-label="Paginación">
      <button className="button button--secondary" type="button" disabled={skip <= 0} onClick={() => onChange(Math.max(0, skip - limit))}>Anterior</button>
      <span>{Math.min(skip + 1, total)}–{Math.min(skip + limit, total)} de {total}</span>
      <button className="button button--secondary" type="button" disabled={skip + limit >= total} onClick={() => onChange(skip + limit)}>Siguiente</button>
    </nav>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium" }).format(new Date(value));
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 2 }).format(value);
}

function stateName(state: Loan["estado"]): string {
  return state.charAt(0).toUpperCase() + state.slice(1);
}

function roleName(role?: string): string {
  return role === "admin" ? "Administración" : role === "bibliotecario" ? "Bibliotecario" : "Socio";
}
