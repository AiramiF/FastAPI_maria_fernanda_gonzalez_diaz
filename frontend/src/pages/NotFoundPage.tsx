import { Link } from "react-router-dom";
import { usePageTitle } from "../components/Primitives";

export function NotFoundPage() {
  usePageTitle("Página no encontrada");
  return (
    <section className="container not-found">
      <p className="eyebrow eyebrow--light">404</p>
      <h1>Esta página no está en nuestro catálogo.</h1>
      <p>Puede que el enlace haya cambiado. Vuelve al catálogo y encuentra otra historia.</p>
      <Link className="button" to="/">Ir al catálogo</Link>
    </section>
  );
}
