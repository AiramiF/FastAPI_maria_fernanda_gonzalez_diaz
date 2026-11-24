import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, queryString } from "../api/client";
import type { Author, Book, Category, Loan, Member, Page, ReportSummary, Role, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { BookCover } from "../components/BookCover";
import { Button, EmptyState, FieldError, RequestError, Skeletons, confirmDelete, usePageTitle } from "../components/Primitives";
import { useToast } from "../components/Toast";

type Section = "resumen" | "libros" | "autores" | "categorias" | "socios" | "prestamos" | "reportes" | "usuarios";

const staffTabs: Array<{ key: Section; label: string }> = [
  { key: "resumen", label: "Resumen" },
  { key: "libros", label: "Libros" },
  { key: "autores", label: "Autores" },
  { key: "categorias", label: "Categorías" },
  { key: "socios", label: "Socios" },
  { key: "prestamos", label: "Préstamos" },
  { key: "reportes", label: "Reportes" },
];

export function StaffPanelPage() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const adminOnly = location.pathname.endsWith("/usuarios");
  const section = adminOnly ? "usuarios" : (location.pathname.split("/")[2] as Section) || "resumen";
  const validSection = staffTabs.some((tab) => tab.key === section) || section === "usuarios";
  usePageTitle(adminOnly ? "Gestión de usuarios" : "Panel de gestión");

  useEffect(() => {
    if (!validSection || (section === "usuarios" && user?.rol !== "admin")) navigate("/panel", { replace: true });
  }, [navigate, section, user?.rol, validSection]);

  return (
    <section className="container page-section panel-page">
      <div className="section-heading panel-heading">
        <div><p className="eyebrow eyebrow--light">Gestión de la biblioteca</p><h1>{adminOnly ? "Usuarios" : "Panel"}</h1></div>
        {user?.rol === "admin" && <Link className="button button--secondary" to={adminOnly ? "/panel" : "/panel/usuarios"}>{adminOnly ? "Volver al panel" : "Gestionar usuarios"}</Link>}
      </div>
      {!adminOnly && (
        <nav className="panel-tabs" aria-label="Secciones del panel">
          {staffTabs.map((tab) => (
            <Link key={tab.key} to={tab.key === "resumen" ? "/panel" : `/panel/${tab.key}`} aria-current={section === tab.key ? "page" : undefined}>{tab.label}</Link>
          ))}
        </nav>
      )}
      <div className="panel-content">
        {section === "resumen" && <SummaryPanel />}
        {section === "libros" && <BooksPanel />}
        {section === "autores" && <AuthorsPanel />}
        {section === "categorias" && <CategoriesPanel />}
        {section === "socios" && <MembersPanel />}
        {section === "prestamos" && <LoansPanel />}
        {section === "reportes" && <ReportsPanel />}
        {section === "usuarios" && user?.rol === "admin" && <UsersPanel />}
      </div>
    </section>
  );
}

function SummaryPanel() {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    void api<ReportSummary>("/reportes/resumen").then((value) => {
      if (active) setSummary(value);
    }).catch((reason: unknown) => {
      if (active) setError(reason);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);
  if (loading) return <Skeletons count={4} />;
  if (error) return <RequestError error={error} retry={() => window.location.reload()} />;
  if (!summary) return <EmptyState title="Sin datos" text="Todavía no hay información para mostrar." />;
  const stats: Array<[string, number | string]> = [
    ["Libros en catálogo", summary.total_libros],
    ["Ejemplares", summary.total_ejemplares],
    ["Préstamos activos", summary.prestados],
    ["Socios activos", summary.socios_activos],
    ["Préstamos vencidos", summary.vencidos],
    ["Multas pendientes", formatMoney(summary.multas)],
  ];
  return <div className="stats-grid">{stats.map(([label, value]) => <article className="stat-card" key={label}><p>{label}</p><strong>{value}</strong></article>)}</div>;
}

interface BookForm {
  titulo: string;
  isbn: string;
  anio_publicacion: string;
  ejemplares: string;
  autor_id: string;
  categoria_ids: number[];
}

const blankBook: BookForm = { titulo: "", isbn: "", anio_publicacion: "", ejemplares: "1", autor_id: "", categoria_ids: [] };

function BooksPanel() {
  const { user } = useAuth();
  const toast = useToast();
  const [books, setBooks] = useState<Book[]>([]);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState<BookForm>(blankBook);
  const [editing, setEditing] = useState<Book | null>(null);
  const [cover, setCover] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [fileError, setFileError] = useState("");
  const canDelete = user?.rol === "admin";

  useEffect(() => () => {
    if (coverPreview.startsWith("blob:")) URL.revokeObjectURL(coverPreview);
  }, [coverPreview]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [bookPage, authorPage, categoryPage] = await Promise.all([
        api<Page<Book>>("/libros?skip=0&limit=100"),
        api<Page<Author>>("/autores?skip=0&limit=100"),
        api<Page<Category> | Category[]>("/categorias?skip=0&limit=100"),
      ]);
      setBooks(bookPage.items);
      setAuthors(authorPage.items);
      setCategories(Array.isArray(categoryPage) ? categoryPage : categoryPage.items);
    } catch (reason) {
      setError(reason);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  const reset = () => {
    setEditing(null);
    setForm(blankBook);
    setCover(null);
    setCoverPreview("");
    setFileError("");
  };

  const chooseCover = (file?: File) => {
    setFileError("");
    setCoverPreview("");
    setCover(null);
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setFileError("Elige una imagen JPEG, PNG o WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setFileError("La imagen no puede superar 5 MB.");
      return;
    }
    setCover(file);
    setCoverPreview(URL.createObjectURL(file));
  };

  const editBook = (book: Book) => {
    setEditing(book);
    setForm({
      titulo: book.titulo,
      isbn: book.isbn,
      anio_publicacion: String(book.anio_publicacion),
      ejemplares: String(book.ejemplares),
      autor_id: String(book.autor.id),
      categoria_ids: book.categorias.map((category) => category.id),
    });
    setCover(null);
    setCoverPreview(book.portada_url ?? "");
    setFileError("");
    document.getElementById("book-editor")?.scrollIntoView({ behavior: "smooth" });
  };

  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        titulo: form.titulo.trim(),
        isbn: form.isbn.trim(),
        anio_publicacion: Number(form.anio_publicacion),
        ejemplares: Number(form.ejemplares),
        autor_id: Number(form.autor_id),
        categoria_ids: form.categoria_ids,
      };
      const saved = editing
        ? await api<Book>(`/libros/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await api<Book>("/libros", { method: "POST", body: JSON.stringify(payload) });
      if (!editing && cover) setEditing(saved);
      if (cover) await uploadCover(saved.id, cover);
      toast.show("success", editing ? "Libro actualizado." : "Libro añadido al catálogo.");
      reset();
      await load();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  };

  const removeBook = async (book: Book) => {
    if (!confirmDelete(`¿Eliminar “${book.titulo}” del catálogo? Esta acción no se puede deshacer.`)) return;
    try {
      await api<void>(`/libros/${book.id}`, { method: "DELETE" });
      toast.show("success", "El libro se eliminó.");
      await load();
    } catch (reason) {
      setError(reason);
    }
  };

  const removeCover = async (book: Book) => {
    if (!confirmDelete(`¿Eliminar la portada de “${book.titulo}”?`)) return;
    try {
      await api<void>(`/libros/${book.id}/portada`, { method: "DELETE" });
      toast.show("success", "La portada se eliminó.");
      await load();
      if (editing?.id === book.id) {
        setEditing({ ...editing, portada_url: null });
        setCoverPreview("");
      }
    } catch (reason) {
      setError(reason);
    }
  };

  const toggleCategory = (id: number) => {
    setForm((current) => ({
      ...current,
      categoria_ids: current.categoria_ids.includes(id)
        ? current.categoria_ids.filter((value) => value !== id)
        : [...current.categoria_ids, id],
    }));
  };

  return (
    <div className="manager-layout">
      <section className="panel-card" id="book-editor">
        <div className="section-heading"><h2>{editing ? "Editar libro" : "Añadir libro"}</h2>{editing && <button className="text-button" type="button" onClick={reset}>Cancelar edición</button>}</div>
        {error !== null && <RequestError error={error} />}
        <form className="form-grid" onSubmit={(event) => void save(event)}>
          <label className="field field--wide">Título<input value={form.titulo} onChange={(event) => setForm({ ...form, titulo: event.target.value })} required /></label>
          <label className="field">ISBN (13 dígitos)<input inputMode="numeric" pattern="\d{13}" maxLength={13} value={form.isbn} onChange={(event) => setForm({ ...form, isbn: event.target.value })} required /></label>
          <label className="field">Año de publicación<input type="number" min={1450} max={new Date().getFullYear()} value={form.anio_publicacion} onChange={(event) => setForm({ ...form, anio_publicacion: event.target.value })} required /></label>
          <label className="field">Ejemplares<input type="number" min={1} max={50} value={form.ejemplares} onChange={(event) => setForm({ ...form, ejemplares: event.target.value })} required /></label>
          <label className="field">Autor<select value={form.autor_id} onChange={(event) => setForm({ ...form, autor_id: event.target.value })} required><option value="">Selecciona un autor</option>{authors.map((author) => <option value={author.id} key={author.id}>{author.nombre}</option>)}</select></label>
          <fieldset className="field field--wide category-picker"><legend>Categorías <span className="field__optional">(elige de 1 a 5)</span></legend><div className="checkbox-grid">{categories.map((category) => <label key={category.id} className="check-option"><input type="checkbox" checked={form.categoria_ids.includes(category.id)} onChange={() => toggleCategory(category.id)} />{capitalize(category.nombre)}</label>)}</div></fieldset>
          <label className="field field--wide">Portada (JPEG, PNG o WebP; máximo 5 MB)<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseCover(event.target.files?.[0])} /><FieldError>{fileError}</FieldError></label>
          {(coverPreview || editing?.portada_url) && (
            <div className="cover-preview">
              <img src={coverPreview || editing?.portada_url || ""} alt="Vista previa de la portada" />
              {editing?.portada_url && !cover && <Button type="button" variant="danger" onClick={() => void removeCover(editing)}>Eliminar portada</Button>}
            </div>
          )}
          <div className="form-actions field--wide"><Button type="submit" disabled={busy || Boolean(fileError)}>{busy ? "Guardando…" : editing ? "Guardar cambios" : "Añadir libro"}</Button></div>
        </form>
      </section>
      <section className="panel-card">
        <div className="section-heading"><h2>Catálogo</h2><span className="result-count">{books.length} títulos</span></div>
        {loading && <Skeletons count={3} />}
        {!loading && error !== null && <RequestError error={error} retry={() => void load()} />}
        {!loading && !error && !books.length && <EmptyState title="Aún no hay libros" text="Añade el primer título al catálogo." />}
        {!loading && books.length > 0 && (
          <div className="managed-book-list">{books.map((book) => (
            <article className="managed-book" key={book.id}>
              <BookCover url={book.portada_url} title={book.titulo} compact />
              <div className="managed-book__details"><h3>{book.titulo}</h3><p>{book.autor.nombre} · {book.anio_publicacion}</p><span>{book.disponibles} de {book.ejemplares} disponibles</span></div>
              <div className="row-actions"><button className="text-button" type="button" onClick={() => editBook(book)}>Editar</button>{canDelete && <button className="text-button text-button--danger" type="button" onClick={() => void removeBook(book)}>Eliminar</button>}</div>
            </article>
          ))}</div>
        )}
      </section>
    </div>
  );
}

async function uploadCover(bookId: number, file: File): Promise<void> {
  const data = new FormData();
  data.append("archivo", file);
  await api<Book>(`/libros/${bookId}/portada`, { method: "POST", body: data });
}

function AuthorsPanel() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState<Author[]>([]);
  const [name, setName] = useState("");
  const [nationality, setNationality] = useState("");
  const [year, setYear] = useState("");
  const [editing, setEditing] = useState<Author | null>(null);
  const [nationalityFilter, setNationalityFilter] = useState("");
  const [selectedAuthor, setSelectedAuthor] = useState<Author | null>(null);
  const [authorBooks, setAuthorBooks] = useState<Book[]>([]);
  const [booksLoading, setBooksLoading] = useState(false);
  const [booksError, setBooksError] = useState<unknown>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const canDelete = user?.rol === "admin";
  const load = async () => {
    setLoading(true);
    try { setItems((await api<Page<Author>>(`/autores${queryString({ skip: 0, limit: 100, nacionalidad: nationalityFilter || undefined })}`)).items); setError(null); }
    catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [nationalityFilter]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = { nombre: name.trim(), nacionalidad: nationality.trim() || null, anio_nacimiento: year ? Number(year) : null };
      if (editing) await api(`/autores/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      else await api("/autores", { method: "POST", body: JSON.stringify(payload) });
      setName(""); setNationality(""); setYear(""); setEditing(null);
      toast.show("success", editing ? "Autor actualizado." : "Autor añadido.");
      await load();
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  const edit = (author: Author) => { setEditing(author); setName(author.nombre); setNationality(author.nacionalidad ?? ""); setYear(author.anio_nacimiento ? String(author.anio_nacimiento) : ""); };
  const remove = async (author: Author) => {
    if (!confirmDelete(`¿Eliminar a ${author.nombre}?`)) return;
    try { await api<void>(`/autores/${author.id}`, { method: "DELETE" }); toast.show("success", "El autor se eliminó."); await load(); }
    catch (reason) { setError(reason); }
  };
  const showAuthorBooks = async (author: Author) => {
    setSelectedAuthor(author);
    setBooksLoading(true);
    setBooksError(null);
    try {
      const result = await api<Page<Book> | Book[]>(`/autores/${author.id}/libros${queryString({ skip: 0, limit: 100 })}`);
      setAuthorBooks(Array.isArray(result) ? result : result.items);
    } catch (reason) {
      setBooksError(reason);
    } finally {
      setBooksLoading(false);
    }
  };

  return (
    <div className="manager-layout">
      <section className="panel-card">
        <h2>{editing ? "Editar autor" : "Añadir autor"}</h2>
        {error !== null && <RequestError error={error} />}
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label className="field field--wide">Nombre<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={100} required /></label>
          <label className="field">Nacionalidad<input value={nationality} onChange={(event) => setNationality(event.target.value)} /></label>
          <label className="field">Año de nacimiento<input type="number" min={1000} value={year} onChange={(event) => setYear(event.target.value)} /></label>
          <div className="form-actions field--wide"><Button type="submit" disabled={busy}>{busy ? "Guardando…" : editing ? "Guardar cambios" : "Añadir autor"}</Button>{editing && <Button type="button" variant="secondary" onClick={() => { setEditing(null); setName(""); setNationality(""); setYear(""); }}>Cancelar</Button>}</div>
        </form>
      </section>
      <DataTable<Author>
        title="Autores"
        rows={items}
        loading={loading}
        error={error}
        retry={() => void load()}
        columns={[["nombre", "Nombre"], ["nacionalidad", "Nacionalidad"], ["anio_nacimiento", "Año"]]}
        header={<label className="field author-filter">Filtrar por nacionalidad<input value={nationalityFilter} onChange={(event) => setNationalityFilter(event.target.value)} /></label>}
        actions={(author) => <><button className="text-button" type="button" onClick={() => void showAuthorBooks(author)}>Ver libros</button><button className="text-button" type="button" onClick={() => edit(author)}>Editar</button>{canDelete && <button className="text-button text-button--danger" type="button" onClick={() => void remove(author)}>Eliminar</button>}</>}
      />
      {selectedAuthor && (
        <section className="panel-card author-books">
          <div className="section-heading"><h2>Libros de {selectedAuthor.nombre}</h2><button className="text-button" type="button" onClick={() => setSelectedAuthor(null)}>Cerrar</button></div>
          {booksLoading && <Skeletons count={2} />}
          {!booksLoading && booksError !== null && <RequestError error={booksError} retry={() => void showAuthorBooks(selectedAuthor)} />}
          {!booksLoading && booksError === null && authorBooks.length === 0 && <EmptyState title="Sin libros" text="Este autor no tiene libros en el catálogo." />}
          {!booksLoading && booksError === null && authorBooks.length > 0 && <ul className="author-book-list">{authorBooks.map((book) => <li key={book.id}><Link to={`/libros/${book.id}`}>{book.titulo}</Link><span>{book.anio_publicacion}</span></li>)}</ul>}
        </section>
      )}
    </div>
  );
}

function CategoriesPanel() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<Category | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const canDelete = user?.rol === "admin";
  const load = async () => {
    setLoading(true);
    try {
      const result = await api<Page<Category> | Category[]>("/categorias?skip=0&limit=100");
      setItems(Array.isArray(result) ? result : result.items);
      setError(null);
    } catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = { nombre: name.trim(), descripcion: description.trim() || null };
      if (editing) await api(`/categorias/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      else await api("/categorias", { method: "POST", body: JSON.stringify(payload) });
      setName(""); setDescription(""); setEditing(null);
      toast.show("success", editing ? "Categoría actualizada." : "Categoría añadida.");
      await load();
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  const remove = async (category: Category) => {
    if (!confirmDelete(`¿Eliminar la categoría ${capitalize(category.nombre)}?`)) return;
    try { await api<void>(`/categorias/${category.id}`, { method: "DELETE" }); toast.show("success", "La categoría se eliminó."); await load(); }
    catch (reason) { setError(reason); }
  };

  return (
    <div className="manager-layout">
      <section className="panel-card">
        <h2>{editing ? "Editar categoría" : "Añadir categoría"}</h2>
        {error !== null && <RequestError error={error} />}
        <form className="form-stack" onSubmit={(event) => void submit(event)}>
          <label className="field">Nombre<input value={name} onChange={(event) => setName(event.target.value)} minLength={3} maxLength={50} required /></label>
          <label className="field">Descripción <span className="field__optional">(opcional)</span><textarea rows={3} maxLength={200} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          <div className="form-actions"><Button type="submit" disabled={busy}>{busy ? "Guardando…" : editing ? "Guardar cambios" : "Añadir categoría"}</Button>{editing && <Button type="button" variant="secondary" onClick={() => { setEditing(null); setName(""); setDescription(""); }}>Cancelar</Button>}</div>
        </form>
      </section>
      <DataTable<Category>
        title="Categorías"
        rows={items}
        loading={loading}
        error={error}
        retry={() => void load()}
        columns={[["nombre", "Nombre"], ["descripcion", "Descripción"]]}
        render={(category, key) => key === "nombre" ? capitalize(category.nombre) : category.descripcion || "—"}
        actions={(category) => <><button className="text-button" type="button" onClick={() => { setEditing(category); setName(category.nombre); setDescription(category.descripcion ?? ""); }}>Editar</button>{canDelete && <button className="text-button text-button--danger" type="button" onClick={() => void remove(category)}>Eliminar</button>}</>}
      />
    </div>
  );
}

function MembersPanel() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState<Member[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const canDelete = user?.rol === "admin";
  const load = async () => {
    setLoading(true);
    try { setItems((await api<Page<Member>>(`/socios${queryString({ skip: 0, limit: 100, activo: activeFilter || undefined })}`)).items); setError(null); }
    catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [activeFilter]);
  const add = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/socios", { method: "POST", body: JSON.stringify({ nombre: name.trim(), email: email.trim(), ...(phone.trim() ? { telefono: phone.trim() } : {}) }) });
      setName(""); setEmail(""); setPhone("");
      toast.show("success", "Socio añadido.");
      await load();
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  const toggleActive = async (member: Member) => {
    try {
      await api(`/socios/${member.id}`, { method: "PATCH", body: JSON.stringify({ activo: !member.activo }) });
      toast.show("success", member.activo ? "Socio desactivado." : "Socio activado.");
      await load();
    } catch (reason) { setError(reason); }
  };
  const remove = async (member: Member) => {
    if (!confirmDelete(`¿Eliminar a ${member.nombre}?`)) return;
    try { await api<void>(`/socios/${member.id}`, { method: "DELETE" }); toast.show("success", "El socio se eliminó."); await load(); }
    catch (reason) { setError(reason); }
  };

  return (
    <div className="manager-layout">
      <section className="panel-card">
        <h2>Añadir socio</h2>
        {error !== null && <RequestError error={error} />}
        <form className="form-grid" onSubmit={(event) => void add(event)}>
          <label className="field">Nombre<input value={name} onChange={(event) => setName(event.target.value)} minLength={3} required /></label>
          <label className="field">Correo<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label className="field">Teléfono <span className="field__optional">(opcional)</span><input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <div className="form-actions field--wide"><Button type="submit" disabled={busy}>{busy ? "Guardando…" : "Añadir socio"}</Button></div>
        </form>
      </section>
      <DataTable<Member>
        title="Socios"
        rows={items}
        loading={loading}
        error={error}
        retry={() => void load()}
        columns={[["nombre", "Nombre"], ["email", "Correo"], ["telefono", "Teléfono"], ["activo", "Estado"]]}
        header={<label className="compact-filter">Estado<select value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)}><option value="">Todos</option><option value="true">Activos</option><option value="false">Inactivos</option></select></label>}
        render={(member, key) => key === "activo" ? <span className={`status-badge ${member.activo ? "status-badge--activo" : "status-badge--devuelto"}`}>{member.activo ? "Activo" : "Inactivo"}</span> : member[key as keyof Member] || "—"}
        actions={(member) => <><Link className="text-button" to={`/panel/socios/${member.id}/prestamos`}>Préstamos</Link><button className="text-button" type="button" onClick={() => void toggleActive(member)}>{member.activo ? "Desactivar" : "Activar"}</button>{canDelete && <button className="text-button text-button--danger" type="button" onClick={() => void remove(member)}>Eliminar</button>}</>}
      />
    </div>
  );
}

function LoansPanel() {
  const toast = useToast();
  const [items, setItems] = useState<Loan[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [bookId, setBookId] = useState("");
  const [memberId, setMemberId] = useState("");
  const [days, setDays] = useState("14");
  const [state, setState] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [loans, bookPage, memberPage] = await Promise.all([
        api<Page<Loan>>(`/prestamos${queryString({ skip: 0, limit: 100, estado: state || undefined })}`),
        api<Page<Book>>("/libros?skip=0&limit=100"),
        api<Page<Member>>("/socios?skip=0&limit=100&activo=true"),
      ]);
      setItems(loans.items);
      setBooks(bookPage.items);
      setMembers(memberPage.items);
    } catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [state]);

  const create = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/prestamos", { method: "POST", body: JSON.stringify({ libro_id: Number(bookId), socio_id: Number(memberId), dias: Number(days) }) });
      setBookId(""); setMemberId(""); setDays("14");
      toast.show("success", "Préstamo registrado.");
      await load();
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  const action = async (loan: Loan, kind: "devolucion" | "pago-multa") => {
    const successMessage = kind === "devolucion" ? "Devolución registrada." : "Pago de multa registrado.";
    try {
      await api<void>(`/prestamos/${loan.id}/${kind}`, { method: "POST" });
      toast.show("success", successMessage);
      await load();
    } catch (reason) { setError(reason); }
  };

  return (
    <div className="manager-layout">
      <section className="panel-card">
        <h2>Registrar préstamo</h2>
        {error !== null && <RequestError error={error} />}
        <form className="form-grid" onSubmit={(event) => void create(event)}>
          <label className="field">Libro<select value={bookId} onChange={(event) => setBookId(event.target.value)} required><option value="">Selecciona un libro</option>{books.filter((book) => book.disponibles > 0).map((book) => <option key={book.id} value={book.id}>{book.titulo} ({book.disponibles} disponibles)</option>)}</select></label>
          <label className="field">Socio<select value={memberId} onChange={(event) => setMemberId(event.target.value)} required><option value="">Selecciona un socio</option>{members.map((member) => <option key={member.id} value={member.id}>{member.nombre} · {member.email}</option>)}</select></label>
          <label className="field">Duración (días)<input type="number" min={1} max={30} value={days} onChange={(event) => setDays(event.target.value)} required /></label>
          <div className="form-actions field--wide"><Button type="submit" disabled={busy}>{busy ? "Registrando…" : "Registrar préstamo"}</Button></div>
        </form>
      </section>
      <section className="panel-card">
        <div className="section-heading"><h2>Préstamos</h2><label className="compact-filter">Estado<select value={state} onChange={(event) => setState(event.target.value)}><option value="">Todos</option><option value="activo">Activo</option><option value="vencido">Vencido</option><option value="devuelto">Devuelto</option></select></label></div>
        {loading && <Skeletons count={2} />}
        {!loading && error !== null && <RequestError error={error} retry={() => void load()} />}
        {!loading && !error && items.length === 0 && <EmptyState title="No hay préstamos" text="Ajusta el filtro o registra un nuevo préstamo." />}
        {!loading && items.length > 0 && (
          <div className="table-wrap">
            <table><thead><tr><th>Libro</th><th>Socio</th><th>Fecha límite</th><th>Estado</th><th>Multa</th><th>Acciones</th></tr></thead>
              <tbody>{items.map((loan) => <tr key={loan.id}>
                <td>{loan.libro.titulo}</td><td>{loan.socio.nombre}<span className="table-subtext">{loan.socio.email}</span></td><td>{formatDate(loan.fecha_limite)}</td><td><span className={`status-badge status-badge--${loan.estado}`}>{capitalize(loan.estado)}</span></td><td>{loan.multa > 0 ? `${formatMoney(loan.multa)}${loan.multa_pagada ? " · pagada" : ""}` : "—"}</td>
                <td className="table-actions">{loan.estado !== "devuelto" && <button className="text-button" type="button" onClick={() => void action(loan, "devolucion")}>Devolver</button>}{loan.multa > 0 && !loan.multa_pagada && <button className="text-button" type="button" onClick={() => void action(loan, "pago-multa")}>Registrar pago</button>}</td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export function MemberLoansHistoryPage() {
  const { id } = useParams();
  const [page, setPage] = useState<Page<Loan> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  usePageTitle("Préstamos del socio");
  useEffect(() => {
    let active = true;
    void api<Page<Loan>>(`/socios/${id}/prestamos${queryString({ skip: 0, limit: 100 })}`)
      .then((result) => { if (active) setPage(result); })
      .catch((reason: unknown) => { if (active) setError(reason); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);
  return (
    <section className="container page-section">
      <Link className="back-link" to="/panel/socios">← Volver a socios</Link>
      <p className="eyebrow eyebrow--light">Gestión de socios</p>
      <h1>Préstamos del socio</h1>
      {loading && <Skeletons count={2} />}
      {!loading && error !== null && <RequestError error={error} retry={() => window.location.reload()} />}
      {!loading && !error && page?.items.length === 0 && <EmptyState title="Sin préstamos" text="Este socio aún no tiene préstamos registrados." />}
      {!loading && !error && page && page.items.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Libro</th><th>Fecha de préstamo</th><th>Fecha límite</th><th>Devolución</th><th>Estado</th></tr></thead>
            <tbody>{page.items.map((loan) => <tr key={loan.id}><td>{loan.libro.titulo}</td><td>{formatDate(loan.fecha_prestamo)}</td><td>{formatDate(loan.fecha_limite)}</td><td>{loan.fecha_devolucion ? formatDate(loan.fecha_devolucion) : "—"}</td><td><span className={`status-badge status-badge--${loan.estado}`}>{capitalize(loan.estado)}</span></td></tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ReportsPanel() {
  const reports = [
    ["Libros más prestados", "/reportes/libros-mas-prestados?limite=10"],
    ["Por categorías", "/reportes/categorias"],
    ["Préstamos vencidos", "/reportes/prestamos-vencidos"],
    ["Socios con multas", "/reportes/socios-con-multas"],
    ["Por autores", "/reportes/autores"],
  ] as const;
  const [active, setActive] = useState<string>(reports[0][1]);
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    void api<Array<Record<string, unknown>>>(active).then((value) => {
      if (mounted) setRows(value);
    }).catch((reason: unknown) => {
      if (mounted) setError(reason);
    }).finally(() => {
      if (mounted) setLoading(false);
    });
    return () => { mounted = false; };
  }, [active, reloadKey]);
  const columns = useMemo(() => rows.length ? Object.keys(rows[0]) : [], [rows]);
  return (
    <section className="panel-card">
      <h2>Reportes</h2>
      <div className="report-tabs" role="group" aria-label="Tipo de reporte">
        {reports.map(([label, path]) => <button key={path} type="button" className={active === path ? "is-active" : ""} aria-pressed={active === path} onClick={() => setActive(path)}>{label}</button>)}
      </div>
      {loading && <Skeletons count={2} />}
      {!loading && error !== null && <RequestError error={error} retry={() => setReloadKey((key) => key + 1)} />}
      {!loading && !error && rows.length === 0 && <EmptyState title="Sin resultados" text="No hay datos disponibles para este reporte." />}
      {!loading && !error && rows.length > 0 && <div className="table-wrap"><table><thead><tr>{columns.map((key) => <th key={key}>{humanize(key)}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map((key) => <td key={key}>{formatReportValue(row[key])}</td>)}</tr>)}</tbody></table></div>}
    </section>
  );
}

function UsersPanel() {
  const toast = useToast();
  const [items, setItems] = useState<User[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "bibliotecario">("bibliotecario");
  const [filterRole, setFilterRole] = useState("");
  const [filterActive, setFilterActive] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const load = async () => {
    setLoading(true);
    try {
      setItems((await api<Page<User>>(`/usuarios${queryString({ skip: 0, limit: 100, rol: filterRole || undefined, activo: filterActive || undefined })}`)).items);
      setError(null);
    } catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [filterRole, filterActive]);
  const create = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/usuarios", { method: "POST", body: JSON.stringify({ email: email.trim(), nombre: name.trim(), password, rol: role }) });
      setEmail(""); setName(""); setPassword("");
      toast.show("success", "Usuario creado.");
      await load();
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  const updateRole = async (person: User, newRole: Role) => {
    if (person.rol === newRole) return;
    try {
      await api(`/usuarios/${person.id}/rol`, { method: "PATCH", body: JSON.stringify({ rol: newRole }) });
      toast.show("success", "Rol actualizado.");
      await load();
    } catch (reason) { setError(reason); }
  };
  const toggleActive = async (person: User) => {
    try {
      await api(`/usuarios/${person.id}/activo`, { method: "PATCH", body: JSON.stringify({ activo: !person.activo }) });
      toast.show("success", person.activo ? "Usuario desactivado." : "Usuario activado.");
      await load();
    } catch (reason) { setError(reason); }
  };
  return (
    <div className="manager-layout">
      <section className="panel-card">
        <h2>Crear usuario de equipo</h2>
        {error !== null && <RequestError error={error} />}
        <form className="form-grid" onSubmit={(event) => void create(event)}>
          <label className="field">Nombre<input value={name} onChange={(event) => setName(event.target.value)} required minLength={3} /></label>
          <label className="field">Correo<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label className="field">Contraseña inicial<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} /></label>
          <label className="field">Rol<select value={role} onChange={(event) => setRole(event.target.value as "admin" | "bibliotecario")}><option value="bibliotecario">Bibliotecario</option><option value="admin">Admin</option></select></label>
          <div className="form-actions field--wide"><Button type="submit" disabled={busy}>{busy ? "Creando…" : "Crear usuario"}</Button></div>
        </form>
      </section>
      <section className="panel-card">
        <div className="section-heading"><h2>Usuarios</h2><div className="filter-inline"><label>Rol<select value={filterRole} onChange={(event) => setFilterRole(event.target.value)}><option value="">Todos</option><option value="admin">Admin</option><option value="bibliotecario">Bibliotecario</option><option value="socio">Socio</option></select></label><label>Estado<select value={filterActive} onChange={(event) => setFilterActive(event.target.value)}><option value="">Todos</option><option value="true">Activos</option><option value="false">Inactivos</option></select></label></div></div>
        {loading && <Skeletons count={2} />}{!loading && error !== null && <RequestError error={error} retry={() => void load()} />}{!loading && !error && !items.length && <EmptyState title="No hay usuarios" text="Cambia los filtros o crea un usuario." />}
        {!loading && items.length > 0 && <div className="table-wrap"><table><thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{items.map((person) => <tr key={person.id}><td>{person.nombre}</td><td>{person.email}</td><td><select className="table-select" aria-label={`Rol de ${person.nombre}`} value={person.rol} onChange={(event) => void updateRole(person, event.target.value as Role)}><option value="admin">Admin</option><option value="bibliotecario">Bibliotecario</option><option value="socio">Socio</option></select></td><td><span className={`status-badge ${person.activo ? "status-badge--activo" : "status-badge--devuelto"}`}>{person.activo ? "Activo" : "Inactivo"}</span></td><td><button className="text-button" type="button" onClick={() => void toggleActive(person)}>{person.activo ? "Desactivar" : "Activar"}</button></td></tr>)}</tbody></table></div>}
      </section>
    </div>
  );
}

function DataTable<T extends { id: number }>({
  title,
  rows,
  loading,
  error,
  retry,
  columns,
  actions,
  render,
  header,
}: {
  title: string;
  rows: T[];
  loading: boolean;
  error: unknown;
  retry: () => void;
  columns: Array<[keyof T, string]>;
  actions?: (row: T) => React.ReactNode;
  render?: (row: T, key: keyof T) => React.ReactNode;
  header?: React.ReactNode;
}) {
  return (
    <section className="panel-card">
      <div className="section-heading"><h2>{title}</h2>{header}</div>
      {loading && <Skeletons count={2} />}
      {!loading && error !== null && <RequestError error={error} retry={retry} />}
      {!loading && !error && !rows.length && <EmptyState title="Sin registros" text="Cuando agregues un elemento, aparecerá aquí." />}
      {!loading && rows.length > 0 && <div className="table-wrap"><table><thead><tr>{columns.map(([, label]) => <th key={label}>{label}</th>)}{actions && <th>Acciones</th>}</tr></thead><tbody>{rows.map((row) => <tr key={row.id}>{columns.map(([key]) => <td key={String(key)}>{render ? render(row, key) : String(row[key] ?? "—")}</td>)}{actions && <td className="table-actions">{actions(row)}</td>}</tr>)}</tbody></table></div>}
    </section>
  );
}

function capitalize(value: string): string {
  return value ? value.charAt(0).toLocaleUpperCase("es") + value.slice(1) : value;
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toLocaleUpperCase("es"));
}

function formatReportValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value) ?? "—";
  return String(value);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium" }).format(new Date(value));
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 2 }).format(value);
}
