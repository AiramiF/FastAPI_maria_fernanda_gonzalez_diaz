# Biblioteca API segura

API REST de biblioteca construida con FastAPI, SQLAlchemy 2, PostgreSQL y Alembic. Implementa autenticación JWT con access y refresh tokens, autorización por roles, validación de datos, préstamos, multas, reportes y migraciones versionadas.

## Arquitectura

```text
app/
├── controllers/  # Reglas de negocio y consultas
├── core/         # Configuración, base de datos, seguridad y dependencias
├── models/       # Modelos SQLAlchemy
├── routes/       # Endpoints HTTP
├── schemas/      # Validación y respuestas Pydantic
├── scripts/      # Utilidades administrativas
└── main.py       # Aplicación FastAPI y middleware
alembic/          # Migraciones de base de datos
tests/            # Pruebas sobre PostgreSQL
```

Los routers se publican bajo `/api/v1`. La configuración se centraliza en `app/core/config.py`; Alembic es el único mecanismo de migración de la aplicación.

## Requisitos previos

- Python 3.12 o superior
- Docker Desktop con el motor Linux activo
- PowerShell

## Instalación paso a paso

Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edita `.env`: reemplaza la clave falsa por el resultado del comando anterior, configura `POSTGRES_PASSWORD` y haz que coincida con la contraseña del rol PostgreSQL. Las contraseñas y claves de ejemplo no son valores de producción. No compartas ni incluyas `.env` en una entrega. Inicia PostgreSQL:

```powershell
docker compose up -d db
```

La primera inicialización del volumen crea `biblioteca` y `biblioteca_test`. Si ya existía el volumen antes de agregar `docker/postgres/init-test-db.sql`, crea una vez la base de pruebas:

```powershell
docker exec biblioteca_db psql -U biblioteca -d postgres -c "CREATE DATABASE biblioteca_test;"
```

## Variables de entorno

Los valores de `.env.example` son marcadores ficticios; debes cambiarlos antes de ejecutar el servicio.

| Variable | Ejemplo ficticio | Uso |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://biblioteca:cambiar_esto@localhost:5434/biblioteca` | Base de datos de desarrollo |
| `TEST_DATABASE_URL` | `postgresql+psycopg://biblioteca:cambiar_esto@localhost:5434/biblioteca_test` | Base exclusiva de pruebas |
| `SECRET_KEY` | `CAMBIAR_POR_UNA_CLAVE_ALEATORIA_DE_MINIMO_32_CARACTERES` | Firma JWT; genera un valor aleatorio de al menos 32 caracteres |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Duración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Duración del refresh token |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Orígenes CORS permitidos |
| `ENVIRONMENT` | `dev` | `dev`, `test` o `prod`; `test` selecciona la base exclusiva de pruebas |
| `POSTGRES_DB` | `biblioteca` | Base principal inicializada por Compose |
| `POSTGRES_USER` | `biblioteca` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | `cambiar_esto` | Contraseña PostgreSQL; reemplázala por un valor seguro |
| `POSTGRES_PORT` | `5434` | Puerto publicado en el host |

`TEST_DATABASE_URL` debe apuntar a una base distinta de `DATABASE_URL`. Compose configura la API con las URL internas de la red Docker.

## Migraciones Alembic

Las migraciones incluidas forman una cadena lineal:

1. `0001_estado_inicial`: autores, categorías, libros, relación libro-categoría, socios y préstamos.
2. `0002_multa_pagada`: agrega `multa_pagada`, asigna pagada a multas en cero y elimina el default temporal.
3. `0003_usuarios`: enum `rolusuario`, tabla de usuarios, índice único por email normalizado y relación opcional 1:1 con socio.
4. `0004_refresh_tokens`: tabla de refresh tokens indexada por `jti`.
5. `0005_auditoria_prestamos`: `prestamos.registrado_por_id`, nullable y con FK a usuarios; los préstamos anteriores quedan sin usuario registrador.

En PowerShell, configura `ENVIRONMENT=dev` para apuntar los comandos a `DATABASE_URL`; para validar una base, apunta `TEST_DATABASE_URL` a la base exclusiva y usa `ENVIRONMENT=test`.

```powershell
alembic current
alembic history
alembic upgrade head
alembic downgrade -1
alembic downgrade base
alembic revision --autogenerate -m "descripcion"
alembic check
```

Revisa siempre una migración autogenerada antes de aplicarla. `alembic downgrade base` elimina el esquema migrado de la base seleccionada.

## Creación del administrador

Con la base de desarrollo migrada, ejecuta:

```powershell
alembic upgrade head
python -m app.scripts.crear_admin
```

El script solicita el correo y lee la contraseña con `getpass`; no guarda contraseñas en el código.

## Ejecución de la API

```powershell
fastapi dev app/main.py
```

Swagger: `http://127.0.0.1:8000/docs`. El health check está en `GET /api/v1/health`. En `ENVIRONMENT=prod` se desactivan `/docs` y `/redoc`.

## Roles del sistema

- **Anónimo:** registro/login/refresh, health y lectura de libros, autores y categorías.
- **Socio:** consulta y actualiza su propio perfil permitido; ve solo sus préstamos y multas. No administra catálogo ni registra préstamos.
- **Bibliotecario:** administra catálogo, socios, préstamos, devoluciones, multas y reportes; no gestiona usuarios ni elimina catálogo/socios.
- **Admin:** permisos de staff, administración de usuarios y operaciones de eliminación reservadas al administrador.

## Reglas de negocio y seguridad

- **R1–R4:** registro valida correo, nombre, contraseña y confirmación; crea usuario con rol socio y un socio vinculado; el email no distingue mayúsculas.
- **R5–R10:** se aplican las restricciones de socio activo, préstamo vencido, máximo de préstamos activos, no duplicar el mismo libro activo, disponibilidad de ejemplares y cálculo de multa de `0.50` por día de retraso.
- **R11:** una multa mayor que cero y no pagada impide nuevos préstamos hasta registrar el pago.
- **A1–A7:** errores de login indistinguibles para correo inexistente/clave incorrecta; usuarios inactivos reciben 403; cinco fallos bloquean 15 minutos; access y refresh son tipos distintos; refresh rota y su reutilización revoca los refresh del usuario; cada request consulta el usuario en la base.
- **Z1–Z7:** autorización por rol; el socio obtiene 404 al pedir un préstamo ajeno y los listados ignoran filtros de socio ajeno; el perfil propio no acepta campos extra; no se puede quitar/desactivar al último admin activo; cambios de rol/estado revocan refresh tokens; un préstamo nuevo registra el usuario staff responsable.

La API usa Argon2 vía `pwdlib`, JWT firmado, limitación de tasa para login/registro, CORS desde settings, `X-Request-ID` y respuestas de error uniformes.

## Endpoints y permisos

`Sí` significa acceso permitido; `Propio` significa acceso limitado a recursos del socio autenticado. `No` indica que la matriz no concede ese acceso.

| Método | Ruta | Descripción | Anónimo | Socio | Bibliotecario | Admin |
|---|---|---|---|---|---|---|
| GET | `/api/v1/health` | Estado de API y base | Sí | Sí | Sí | Sí |
| POST | `/api/v1/auth/registro` | Registro de socio | Sí | Sí | Sí | Sí |
| POST | `/api/v1/auth/login` | Iniciar sesión | Sí | Sí | Sí | Sí |
| POST | `/api/v1/auth/refresh` | Renovar tokens | Sí | Sí | Sí | Sí |
| POST | `/api/v1/auth/logout` | Cerrar sesiones refresh del usuario | No | Sí | Sí | Sí |
| GET | `/api/v1/auth/me` | Perfil autenticado | No | Sí | Sí | Sí |
| PATCH | `/api/v1/auth/me/password` | Cambiar contraseña | No | Sí | Sí | Sí |
| GET | `/api/v1/autores` | Lista paginada de autores | Sí | Sí | Sí | Sí |
| GET | `/api/v1/autores/{autor_id}` | Detalle de autor | Sí | Sí | Sí | Sí |
| GET | `/api/v1/autores/{autor_id}/libros` | Libros de un autor | Sí | Sí | Sí | Sí |
| POST | `/api/v1/autores` | Crear autor | No | No | Sí | Sí |
| PATCH | `/api/v1/autores/{autor_id}` | Editar autor | No | No | Sí | Sí |
| DELETE | `/api/v1/autores/{autor_id}` | Eliminar autor | No | No | No | Sí |
| GET | `/api/v1/categorias` | Lista paginada de categorías | Sí | Sí | Sí | Sí |
| POST | `/api/v1/categorias` | Crear categoría | No | No | Sí | Sí |
| PATCH | `/api/v1/categorias/{categoria_id}` | Editar categoría | No | No | Sí | Sí |
| DELETE | `/api/v1/categorias/{categoria_id}` | Eliminar categoría | No | No | No | Sí |
| GET | `/api/v1/libros` | Lista paginada y filtrable | Sí | Sí | Sí | Sí |
| GET | `/api/v1/libros/{libro_id}` | Detalle de libro | Sí | Sí | Sí | Sí |
| POST | `/api/v1/libros` | Crear libro | No | No | Sí | Sí |
| PATCH | `/api/v1/libros/{libro_id}` | Editar libro | No | No | Sí | Sí |
| DELETE | `/api/v1/libros/{libro_id}` | Eliminar libro | No | No | No | Sí |
| GET | `/api/v1/socios` | Lista paginada de socios | No | No | Sí | Sí |
| POST | `/api/v1/socios` | Crear socio | No | No | Sí | Sí |
| GET | `/api/v1/socios/me` | Perfil propio | No | Propio | No | No |
| PATCH | `/api/v1/socios/me` | Editar campos permitidos del perfil propio | No | Propio | No | No |
| GET | `/api/v1/socios/me/prestamos` | Préstamos propios | No | Propio | No | No |
| GET | `/api/v1/socios/me/multas` | Multas propias pendientes | No | Propio | No | No |
| GET | `/api/v1/socios/{socio_id}` | Detalle de socio | No | No | Sí | Sí |
| PATCH | `/api/v1/socios/{socio_id}` | Editar socio | No | No | Sí | Sí |
| DELETE | `/api/v1/socios/{socio_id}` | Eliminar/desactivar socio | No | No | No | Sí |
| GET | `/api/v1/socios/{socio_id}/prestamos` | Préstamos de un socio | No | No | Sí | Sí |
| GET | `/api/v1/prestamos` | Lista filtrada de préstamos | No | Propio | Sí | Sí |
| GET | `/api/v1/prestamos/{prestamo_id}` | Detalle de préstamo | No | Propio | Sí | Sí |
| POST | `/api/v1/prestamos` | Registrar préstamo | No | No | Sí | Sí |
| POST | `/api/v1/prestamos/{prestamo_id}/devolucion` | Registrar devolución | No | No | Sí | Sí |
| POST | `/api/v1/prestamos/{prestamo_id}/pago-multa` | Registrar pago de multa | No | No | Sí | Sí |
| GET | `/api/v1/reportes/libros-mas-prestados` | Libros más prestados | No | No | Sí | Sí |
| GET | `/api/v1/reportes/categorias` | Reporte por categorías | No | No | Sí | Sí |
| GET | `/api/v1/reportes/prestamos-vencidos` | Préstamos vencidos | No | No | Sí | Sí |
| GET | `/api/v1/reportes/socios-con-multas` | Socios con multas | No | No | Sí | Sí |
| GET | `/api/v1/reportes/autores` | Reporte por autores | No | No | Sí | Sí |
| GET | `/api/v1/reportes/resumen` | Resumen general | No | No | Sí | Sí |
| GET | `/api/v1/usuarios` | Lista paginada de usuarios | No | No | No | Sí |
| POST | `/api/v1/usuarios` | Crear usuario staff | No | No | No | Sí |
| PATCH | `/api/v1/usuarios/{usuario_id}/rol` | Cambiar rol | No | No | No | Sí |
| PATCH | `/api/v1/usuarios/{usuario_id}/activo` | Activar/desactivar usuario | No | No | No | Sí |

## Pruebas

Las pruebas usan `TEST_DATABASE_URL`, crean el esquema mediante `alembic upgrade head`, limpian las tablas entre casos y reinician el rate limiter. No usan `create_all`.

En PowerShell, selecciona el entorno de pruebas para que SQLAlchemy y Alembic apunten a `TEST_DATABASE_URL`:

```powershell
$env:ENVIRONMENT = "test"
pytest --cov=app --cov-report=term-missing -q
$env:ENVIRONMENT = "dev"
```

La URL de pruebas debe ser una base PostgreSQL exclusiva y distinta de la base de desarrollo. La fixture verifica esa condición antes de ejecutar migraciones destructivas.

## Docker

Compose levanta PostgreSQL 16 con healthcheck, inicializa `biblioteca_test` en un volumen nuevo y ofrece un servicio opcional `api` que aplica migraciones antes de iniciar Uvicorn:

```powershell
docker compose config --quiet
docker compose up -d db
docker compose up --build
```

`.dockerignore` excluye `.env`, entornos virtuales, cachés, bases locales y documentación del contexto de construcción.

## Integrantes

Completa los nombres antes de entregar:

| Nombre completo | Rol |
|---|---|
| Nombre Apellido | Aprendiz |
| Nombre Apellido | Aprendiz |

## Preparación del ZIP

Incluye `app/`, `alembic/`, `tests/` (solo archivos fuente), `docker/`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `alembic.ini`, `requirements.txt`, `requirements-dev.txt`, `.env.example` y `README.md`.

Excluye `.env`, `.venv/`, `.git/`, `.vscode/`, `.idea/`, `__pycache__/`, `.pytest_cache/`, `.coverage`, archivos `*.pyc`, `*.db`, `*.log` y temporales. Antes de comprimir, revisa que `.env.example` siga usando únicamente los marcadores ficticios.
