import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, queryString } from "../api/client";
import type { Book, Category, Page } from "../api/types";
import { BookCover } from "../components/BookCover";
import { EmptyState, RequestError, Skeletons, usePageTitle } from "../components/Primitives";

const PAGE_SIZE = 20;

export function CatalogPage() {
  usePageTitle("Catálogo");
  const [searchParams, setSearchParams] = useSearchParams();
  const [books, setBooks] = useState<Page<Book> | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [search, setSearch] = useState(searchParams.get("buscar") ?? "");
  const [author, setAuthor] = useState(searchParams.get("autor") ?? "");
  const [category, setCategory] = useState(searchParams.get("categoria_id") ?? "");
  const [order, setOrder] = useState(searchParams.get("orden") ?? "titulo");
  const skip = Number(searchParams.get("skip") ?? "0");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void Promise.all([
      api<Page<Book>>(`/libros${queryString({
        skip,
        limit: PAGE_SIZE,
        buscar: searchParams.get("buscar") ?? "",
        autor: searchParams.get("autor") ?? "",
        categoria_id: searchParams.get("categoria_id") ?? "",
        orden: searchParams.get("orden") ?? "titulo",
      })}`),
      api<Page<Category> | Category[]>(`/categorias${queryString({ limit: 100 })}`),
    ]).then(([bookPage, categoryResult]) => {
      if (!active) return;
      setBooks(bookPage);
      setCategories(Array.isArray(categoryResult) ? categoryResult : categoryResult.items);
    }).catch((reason: unknown) => {
      if (active) setError(reason);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [searchParams, skip, reloadKey]);

  const applyFilters = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams();
    if (search.trim()) params.set("buscar", search.trim());
    if (author.trim()) params.set("autor", author.trim());
    if (category) params.set("categoria_id", category);
    if (order) params.set("orden", order);
    setSearchParams(params);
  };

  const goToPage = (nextSkip: number) => {
    const params = new URLSearchParams(searchParams);
    if (nextSkip) params.set("skip", String(nextSkip));
    else params.delete("skip");
    setSearchParams(params);
  };

  return (
    <>
      <section className="catalog-hero">
        <div className="container catalog-hero__inner">
          <div className="catalog-hero__copy">
            <p className="eyebrow">Tu próxima historia te espera</p>
            <h1>Encuentra un libro<br />que te acompañe.</h1>
            <p>Explora nuestra colección y descubre lecturas para cada momento.</p>
          </div>
          <form className="catalog-search" onSubmit={applyFilters} role="search" aria-label="Buscar en el catálogo">
            <label htmlFor="book-search">Buscar por título</label>
            <div className="catalog-search__input">
              <input
                id="book-search"
                name="buscar"
                placeholder="¿Qué te gustaría leer?"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <button type="submit" className="button">Buscar</button>
            </div>
            <div className="filter-row">
              <label>
                Autor
                <input value={author} onChange={(event) => setAuthor(event.target.value)} placeholder="Nombre del autor" />
              </label>
              <label>
                Categoría
                <select value={category} onChange={(event) => setCategory(event.target.value)}>
                  <option value="">Todas</option>
                  {categories.map((item) => <option value={item.id} key={item.id}>{displayCategory(item.nombre)}</option>)}
                </select>
              </label>
              <label>
                Ordenar
                <select value={order} onChange={(event) => setOrder(event.target.value)}>
                  <option value="titulo">Título A–Z</option>
                  <option value="anio">Más antiguos</option>
                  <option value="-anio">Más recientes</option>
                </select>
              </label>
              <button type="submit" className="hero-filter-button">Aplicar filtros</button>
            </div>
          </form>
        </div>
      </section>

      <section className="container catalog-section" aria-labelledby="catalog-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow eyebrow--light">Colección</p>
            <h2 id="catalog-title">Libros para descubrir</h2>
          </div>
          {books && <p className="result-count">{books.total} {books.total === 1 ? "libro" : "libros"}</p>}
        </div>
        {loading && <Skeletons />}
        {!loading && error !== null && <RequestError error={error} retry={() => setReloadKey((key) => key + 1)} />}
        {!loading && !error && books?.items.length === 0 && (
          <EmptyState title="No encontramos libros" text="Prueba con otros términos o quita algunos filtros." />
        )}
        {!loading && !error && books && books.items.length > 0 && (
          <>
            <div className="book-grid">
              {books.items.map((book) => (
                <article className="book-card" key={book.id}>
                  <Link className="book-card__cover-link" to={`/libros/${book.id}`} aria-label={`Ver ${book.titulo}`}>
                    <BookCover url={book.portada_url} title={book.titulo} />
                  </Link>
                  <div className="book-card__body">
                    <h3><Link to={`/libros/${book.id}`}>{book.titulo}</Link></h3>
                    <p className="book-card__author">{book.autor.nombre}</p>
                    <div className="badge-row">
                      {book.categorias.slice(0, 3).map((item) => (
                        <span className="badge" key={item.id}>{displayCategory(item.nombre)}</span>
                      ))}
                    </div>
                    <span className={`availability${book.disponibles < 1 ? " availability--none" : ""}`}>
                      {book.disponibles} {book.disponibles === 1 ? "disponible" : "disponibles"}
                    </span>
                  </div>
                </article>
              ))}
            </div>
            <nav className="pagination" aria-label="Paginación del catálogo">
              <button className="button button--secondary" type="button" disabled={skip <= 0} onClick={() => goToPage(Math.max(0, skip - PAGE_SIZE))}>Anterior</button>
              <span>Mostrando {skip + 1}–{Math.min(skip + PAGE_SIZE, books.total)} de {books.total}</span>
              <button className="button button--secondary" type="button" disabled={skip + PAGE_SIZE >= books.total} onClick={() => goToPage(skip + PAGE_SIZE)}>Siguiente</button>
            </nav>
          </>
        )}
      </section>
    </>
  );
}

function displayCategory(name: string): string {
  return name ? name.charAt(0).toLocaleUpperCase("es") + name.slice(1) : name;
}
