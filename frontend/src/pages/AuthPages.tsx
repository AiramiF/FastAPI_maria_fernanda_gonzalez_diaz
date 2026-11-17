import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, FieldError, usePageTitle } from "../components/Primitives";
import { useToast } from "../components/Toast";

interface Registration {
  email: string;
  nombre: string;
  telefono: string;
  password: string;
  confirmar_password: string;
}

export function LoginPage() {
  usePageTitle("Iniciar sesión");
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrors({});
    setMessage("");
    setBusy(true);
    try {
      await login(email.trim(), password);
      toast.show("success", "¡Qué bueno verte de nuevo!");
      const target = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(target, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(error.fieldErrors);
        setMessage(loginError(error));
      } else {
        setMessage("No pudimos conectar con el servicio. Inténtalo de nuevo.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow eyebrow--light">Bienvenido de vuelta</p>
        <h1>Iniciar sesión</h1>
        <p className="auth-card__intro">Continúa tu camino de lectura.</p>
        {message && <div className="notice notice--error" role="alert"><span className="notice__icon" aria-hidden="true">!</span><p>{message}</p></div>}
        <form className="form-stack" onSubmit={submit} noValidate>
          <label className="field">
            Correo electrónico
            <input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} aria-invalid={Boolean(errors.email)} />
            <FieldError>{errors.email}</FieldError>
          </label>
          <label className="field">
            Contraseña
            <span className="password-field">
              <input type={showPassword ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={Boolean(errors.password)} />
              <button className="password-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}>{showPassword ? "Ocultar" : "Mostrar"}</button>
            </span>
            <FieldError>{errors.password}</FieldError>
          </label>
          <Button type="submit" disabled={busy}>{busy ? "Ingresando…" : "Ingresar"}</Button>
        </form>
        <p className="auth-card__foot">¿Aún no tienes cuenta? <Link to="/registro">Regístrate</Link></p>
      </div>
    </section>
  );
}

export function RegisterPage() {
  usePageTitle("Crear cuenta");
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState<Registration>({ email: "", nombre: "", telefono: "", password: "", confirmar_password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key: keyof Registration, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const validate = (): Record<string, string> => {
    const next: Record<string, string> = {};
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) next.email = "Escribe un correo electrónico válido.";
    if (form.nombre.trim().length < 3) next.nombre = "El nombre debe tener al menos 3 caracteres.";
    if (form.telefono && (!/^[\d +]+$/.test(form.telefono) || form.telefono.length < 7 || form.telefono.length > 15)) {
      next.telefono = "Usa de 7 a 15 caracteres: números, espacios o +.";
    }
    if (form.password.length < 8 || form.password.length > 64 || !/[A-Z]/.test(form.password) || !/[a-z]/.test(form.password) || !/\d/.test(form.password)) {
      next.password = "Usa entre 8 y 64 caracteres, con mayúscula, minúscula y número.";
    }
    if (form.confirmar_password !== form.password) next.confirmar_password = "Las contraseñas no coinciden.";
    return next;
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const validation = validate();
    setErrors(validation);
    setMessage("");
    if (Object.keys(validation).length) return;
    setBusy(true);
    try {
      await api("/auth/registro", {
        method: "POST",
        body: JSON.stringify({
          email: form.email.trim(),
          nombre: form.nombre.trim(),
          ...(form.telefono.trim() ? { telefono: form.telefono.trim() } : {}),
          password: form.password,
          confirmar_password: form.confirmar_password,
        }),
        skipRefresh: true,
      });
      toast.show("success", "Tu cuenta está lista. Ya puedes iniciar sesión.");
      navigate("/login", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors((current) => ({ ...current, ...error.fieldErrors }));
        setMessage(error.message);
      } else {
        setMessage("No pudimos conectar con el servicio. Inténtalo de nuevo.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="auth-page auth-page--register">
      <div className="auth-card">
        <p className="eyebrow eyebrow--light">Un espacio para tus historias</p>
        <h1>Crea tu cuenta</h1>
        <p className="auth-card__intro">Regístrate para llevar tus lecturas contigo.</p>
        {message && <div className="notice notice--error" role="alert"><span className="notice__icon" aria-hidden="true">!</span><p>{message}</p></div>}
        <form className="form-stack" onSubmit={submit} noValidate>
          <label className="field">Nombre completo<input autoComplete="name" value={form.nombre} onChange={(event) => update("nombre", event.target.value)} aria-invalid={Boolean(errors.nombre)} /><FieldError>{errors.nombre}</FieldError></label>
          <label className="field">Correo electrónico<input type="email" autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} aria-invalid={Boolean(errors.email)} /><FieldError>{errors.email}</FieldError></label>
          <label className="field">Teléfono <span className="field__optional">(opcional)</span><input type="tel" autoComplete="tel" value={form.telefono} onChange={(event) => update("telefono", event.target.value)} aria-invalid={Boolean(errors.telefono)} /><FieldError>{errors.telefono}</FieldError></label>
          <label className="field">Contraseña<span className="password-field"><input type={showPassword ? "text" : "password"} autoComplete="new-password" value={form.password} onChange={(event) => update("password", event.target.value)} aria-invalid={Boolean(errors.password)} /><button className="password-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}>{showPassword ? "Ocultar" : "Mostrar"}</button></span><FieldError>{errors.password}</FieldError></label>
          <label className="field">Confirmar contraseña<span className="password-field"><input type={showConfirm ? "text" : "password"} autoComplete="new-password" value={form.confirmar_password} onChange={(event) => update("confirmar_password", event.target.value)} aria-invalid={Boolean(errors.confirmar_password)} /><button className="password-toggle" type="button" onClick={() => setShowConfirm((value) => !value)} aria-label={showConfirm ? "Ocultar contraseña" : "Mostrar contraseña"}>{showConfirm ? "Ocultar" : "Mostrar"}</button></span><FieldError>{errors.confirmar_password}</FieldError></label>
          <Button type="submit" disabled={busy}>{busy ? "Creando cuenta…" : "Crear cuenta"}</Button>
        </form>
        <p className="auth-card__foot">¿Ya tienes una cuenta? <Link to="/login">Inicia sesión</Link></p>
      </div>
    </section>
  );
}

function loginError(error: ApiError): string {
  if (error.status === 423) return "Tu cuenta está temporalmente bloqueada por varios intentos. Espera unos minutos antes de volver a intentarlo.";
  if (error.status === 403) return "Tu cuenta está inactiva. Contacta con el equipo de la biblioteca.";
  if (error.status === 429) return "Demasiados intentos. Espera un momento antes de volver a probar.";
  if (error.status === 401) return "El correo o la contraseña no son correctos.";
  return error.message;
}
