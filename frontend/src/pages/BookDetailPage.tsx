import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Book } from "../api/types";
import { BookCover } from "../components/BookCover";
import { Button, EmptyState, RequestError, Skeletons, usePageTitle } from "../components/Primitives";

export function BookDetailPage() {
  const { id } = useParams();
  const [book, setBook] = useState<Book | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  usePageTitle(book?.titulo ?? "Detalle del libro");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void api<Book>(`/libros/${id}`).then((result) => {
      if (active) setBook(result);
    }).catch((reason: unknown) => {
      if (active) setError(reason);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [id]);

  return (
    <section className="container page-section">
      <Link className="back-link" to="/">← Volver al catálogo</Link>
      {loading && <div className="detail-skeleton"><Skeletons count={1} /></div>}
      {!loading && error !== null && <RequestError error={error} retry={() => window.location.reload()} />}
      {!loading && !error && !book && <EmptyState title="Libro no encontrado" text="Puede que este título ya no esté en el catálogo." />}
      {!loading && !error && book && (
        <article className="book-detail">
          <BookCover url={book.portada_url} title={book.titulo} />
          <div className="book-detail__content">
            <p className="eyebrow eyebrow--light">Ficha del libro</p>
            <h1>{book.titulo}</h1>
            <p className="book-detail__author">{book.autor.nombre}</p>
            <div className="badge-row">
              {book.categorias.map((category) => <span className="badge" key={category.id}>{category.nombre.charAt(0).toLocaleUpperCase("es") + category.nombre.slice(1)}</span>)}
            </div>
            <dl className="book-facts">
              <div><dt>Año de publicación</dt><dd>{book.anio_publicacion}</dd></div>
              <div><dt>ISBN</dt><dd>{book.isbn}</dd></div>
              <div><dt>Ejemplares</dt><dd>{book.ejemplares}</dd></div>
              <div><dt>Disponibilidad</dt><dd>{book.disponibles} disponibles</dd></div>
            </dl>
            <Button type="button" onClick={() => window.history.back()} variant="secondary">Seguir explorando</Button>
          </div>
        </article>
      )}
    </section>
  );
}
