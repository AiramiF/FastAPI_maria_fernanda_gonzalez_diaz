import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth, isStaff } from "../auth/AuthContext";
import { BookIcon } from "./BookCover";
import { useToast } from "./Toast";

function NavigationLinks({ close }: { close: () => void }) {
  const { user } = useAuth();
  return (
    <>
      <NavLink to="/" end onClick={close}>Catálogo</NavLink>
      {user?.rol === "socio" && <NavLink to="/mis-prestamos" onClick={close}>Mis préstamos</NavLink>}
      {user?.rol === "socio" && <NavLink to="/mis-multas" onClick={close}>Mis multas</NavLink>}
      {isStaff(user?.rol) && <NavLink to="/panel" onClick={close}>Panel</NavLink>}
    </>
  );
}

export function Layout() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  const signOut = async () => {
    try {
      await logout();
    } catch {
      toast.show("error", "La sesión se cerró, pero no se pudo confirmar con el servidor.");
    }
    setMenuOpen(false);
    navigate("/", { replace: true });
  };

  return (
    <div className="site-shell">
      <a className="skip-link" href="#contenido">Saltar al contenido</a>
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" to="/" aria-label="Biblioteca, ir al catálogo">
            <BookIcon className="brand__icon" />
            <span>Biblioteca</span>
          </Link>
          <nav className="desktop-nav" aria-label="Navegación principal"><NavigationLinks close={() => undefined} /></nav>
          <div className="header-actions">
            {user ? (
              <details className="user-menu">
                <summary aria-label={`Menú de ${user.nombre}`}>{user.nombre}<span aria-hidden="true">⌄</span></summary>
                <div className="user-menu__panel">
                  <Link to="/perfil">Mi perfil</Link>
                  <button type="button" onClick={() => void signOut()}>Cerrar sesión</button>
                </div>
              </details>
            ) : (
              <>
                <Link className="header-login" to="/login">Iniciar sesión</Link>
                <Link className="button button--small" to="/registro">Crear cuenta</Link>
              </>
            )}
            <button
              className={`menu-toggle${menuOpen ? " is-open" : ""}`}
              type="button"
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              aria-label={menuOpen ? "Cerrar menú" : "Abrir menú"}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <span /><span /><span />
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav className="mobile-nav" id="mobile-navigation" aria-label="Navegación móvil">
            <NavigationLinks close={() => setMenuOpen(false)} />
            {user && <Link to="/perfil" onClick={() => setMenuOpen(false)}>Mi perfil</Link>}
            {user && <button type="button" onClick={() => void signOut()}>Cerrar sesión</button>}
          </nav>
        )}
      </header>
      <main id="contenido" className="main-content"><Outlet /></main>
      <footer className="site-footer">
        <div className="footer-inner">
          <Link className="brand brand--footer" to="/"><BookIcon className="brand__icon" /><span>Biblioteca</span></Link>
          <p>Un lugar para encontrar tu próxima lectura.</p>
          <span>© {new Date().getFullYear()} Biblioteca</span>
        </div>
      </footer>
    </div>
  );
}
