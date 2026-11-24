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
- PostgreSQL 16 instalado y ejecutándose localmente
- PowerShell
- PowerShell

## Instalación paso a paso

Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edita `.env`: reemplaza la clave falsa por el resultado del comando anterior y configura ambas URL para PostgreSQL local. Por ejemplo, en el puerto predeterminado 5432:

```env
DATABASE_URL=postgresql+psycopg://postgres:TU_CONTRASEÑA@localhost:5432/biblioteca
TEST_DATABASE_URL=postgresql+psycopg://postgres:TU_CONTRASEÑA@localhost:5432/biblioteca_test
```

Las contraseñas y claves de ejemplo no son valores de producción. No compartas ni incluyas `.env` en una entrega. Crea ambas bases de datos:

```powershell
psql -U postgres -c "CREATE DATABASE biblioteca;"
psql -U postgres -c "CREATE DATABASE biblioteca_test;"
alembic upgrade head
```

## Variables de entorno

Los valores de `.env.example` son marcadores ficticios; debes cambiarlos antes de ejecutar el servicio.

| Variable | Ejemplo ficticio | Uso |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://biblioteca:cambiar_esto@localhost:5432/biblioteca` | Base de datos de desarrollo |
| `TEST_DATABASE_URL` | `postgresql+psycopg://biblioteca:cambiar_esto@localhost:5432/biblioteca_test` | Base exclusiva de pruebas |
| `SECRET_KEY` | `CAMBIAR_POR_UNA_CLAVE_ALEATORIA_DE_MINIMO_32_CARACTERES` | Firma JWT; genera un valor aleatorio de al menos 32 caracteres |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Duración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Duración del refresh token |
| `CLOUDINARY_CLOUD_NAME` | `nombre_de_nube_ficticio` | Nombre de nube de Cloudinary |
| `CLOUDINARY_API_KEY` | `clave_api_ficticia` | Clave API de Cloudinary |
| `CLOUDINARY_API_SECRET` | `secreto_cloudinary_ficticio` | Secreto API de Cloudinary |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Orígenes CORS permitidos |
| `ENVIRONMENT` | `dev` | `dev`, `test` o `prod`; `test` selecciona la base exclusiva de pruebas |

`TEST_DATABASE_URL` debe apuntar a una base distinta de `DATABASE_URL`.

## Migraciones Alembic

Las migraciones incluidas forman una cadena lineal:

1. `0001_estado_inicial`: autores, categorías, libros, relación libro-categoría, socios y préstamos.
2. `0002_multa_pagada`: agrega `multa_pagada`, asigna pagada a multas en cero y elimina el default temporal.
3. `0003_usuarios`: enum `rolusuario`, tabla de usuarios, índice único por email normalizado y relación opcional 1:1 con socio.
4. `0004_refresh_tokens`: tabla de refresh tokens indexada por `jti`.
5. `0005_auditoria_prestamos`: `prestamos.registrado_por_id`, nullable y con FK a usuarios; los préstamos anteriores quedan sin usuario registrador.
6. `0006_portada_libros`: agrega URL e identificador Cloudinary nullable a los libros; los libros existentes quedan sin portada.

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
| POST | `/api/v1/libros/{libro_id}/portada` | Subir/reemplazar portada (JPEG, PNG o WebP; máximo 5 MB) | No | No | Sí | Sí |
| DELETE | `/api/v1/libros/{libro_id}/portada` | Eliminar portada | No | No | Sí | Sí |
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

## Frontend

Requiere Node.js y npm. Desde la raíz del proyecto:

```powershell
Set-Location frontend
npm install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm run dev
```

Vite abre `http://localhost:3000`. `VITE_API_URL` configura la API y, si no se define, usa `http://localhost:8000/api/v1`.

## Iniciar todo el proyecto en local

Completa primero la instalación y configura el `.env` de la raíz. Asegúrate de que el servicio local de PostgreSQL 16 esté ejecutándose y que `DATABASE_URL` apunte a `biblioteca`, mientras que `TEST_DATABASE_URL` apunte a `biblioteca_test`.

1. Solo la primera vez, crea las bases de desarrollo y pruebas:

   ```powershell
   psql -U postgres -c "CREATE DATABASE biblioteca;"
   psql -U postgres -c "CREATE DATABASE biblioteca_test;"
   ```

2. En la terminal de backend, desde la raíz del repositorio, activa el entorno, aplica las migraciones y, opcionalmente, crea los datos demo:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   $env:ENVIRONMENT = "dev"
   alembic upgrade head
   python -m app.scripts.seed_demo
   ```

   El seed es opcional; está pensado para desarrollo/demo. No se ejecuta con `ENVIRONMENT=prod`.

3. En esa misma terminal, inicia la API y déjala ejecutándose:

   ```powershell
   fastapi dev app/main.py
   ```

4. Abre otra terminal para el frontend:

   ```powershell
   Set-Location frontend
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   npm install                  # solo la primera vez o al cambiar dependencias
   npm run dev
   ```

5. Abre `http://localhost:3000`. La API está en `http://localhost:8000`; Swagger está en `http://localhost:8000/docs`. Para detener los servicios, pulsa `Ctrl+C` en ambas terminales.

Si el navegador muestra un error CORS, verifica que `CORS_ORIGINS` incluya `http://localhost:3000` sin barra final y que `frontend/.env` tenga `VITE_API_URL=http://localhost:8000/api/v1`.

## Usuarios de demostración

Con la base de desarrollo migrada, ejecuta:

```powershell
python -m app.scripts.seed_demo
```

| Email | Contraseña | Rol |
|---|---|---|
| `admin@biblioteca.com` | `Biblioteca2026` | Administrador |
| `socio@biblioteca.com` | `Biblioteca2026` | Socio |

Solo para desarrollo/demo; cambiar antes de producción; el script no corre con `ENVIRONMENT=prod`.

Las portadas se ven solo si el libro tiene portada (subida desde `/panel > Libros` o por el seed); si no, se muestra un placeholder.

## Publicar en GitHub y Vercel

### 1. Subir el código a GitHub

Antes de subir, revisa que los archivos de entorno no estén versionados:

```powershell
git status --short
git check-ignore .env frontend/.env
git ls-files .env frontend/.env
```

`.gitignore` excluye los archivos `.env`; nunca publiques sus valores, claves JWT ni credenciales de Cloudinary. Si `git ls-files` muestra algún archivo de entorno, quita del índice cada archivo que aparezca con `git rm --cached <archivo>` (esto conserva la copia local) y cambia cualquier secreto que ya se haya subido.

Después crea un repositorio en GitHub. Desde la raíz del proyecto, revisa los archivos con `git status`, crea un commit y configura el remoto si aún no existe:

```powershell
git add .
git commit -m "Preparar despliegue"
git remote add origin https://github.com/<usuario>/<repositorio>.git
git branch --show-current
git push -u origin <rama>
```

Si `origin` ya existe, no repitas `git remote add`; verifica con `git remote -v`. Reemplaza `<rama>` por el nombre mostrado por `git branch --show-current`. Luego importa ese repositorio desde Vercel.

### 2. Desplegar el frontend

En Vercel, crea un proyecto desde el repositorio y configura:

- **Root Directory:** `frontend`
- **Framework Preset:** Vite
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variable:** `VITE_API_URL=https://<dominio-del-backend>/api/v1`

`VITE_API_URL` se incorpora durante el build; vuelve a desplegar el frontend después de cambiarlo. No uses `localhost` en producción.

### 3. Desplegar la API

Puedes crear un segundo proyecto Vercel desde el mismo repositorio, con la raíz del repositorio como **Root Directory**. Vercel soporta FastAPI en el runtime de Python y reconoce `app/main.py` como punto de entrada. Configura las variables secretas desde el panel de Vercel, no en GitHub:

- `DATABASE_URL`: URL de una base PostgreSQL accesible desde Vercel, mientras la aplicación siga usando PostgreSQL.
- `SECRET_KEY`: clave de producción nueva y aleatoria.
- `ENVIRONMENT=prod`.
- `CORS_ORIGINS`: arreglo JSON con el origen exacto del frontend, por ejemplo `["https://<dominio-del-frontend>"]`.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` y `CLOUDINARY_API_SECRET`, si vas a usar las portadas.

Primero despliega la API; luego configura su URL en `VITE_API_URL` del proyecto frontend y vuelve a desplegarlo. Ejecuta las migraciones de Alembic una sola vez contra la base de producción antes de habilitar tráfico; no las ejecutes al importar la aplicación ni en cada solicitud. Comprueba `/api/v1/health` y el login después del despliegue.

La API en Vercel funciona como funciones serverless: usa servicios externos para la base de datos y los archivos; no dependas de archivos locales persistentes. Para más detalles, consulta la [guía oficial de FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

## Migrar de PostgreSQL a MongoDB

**Sí es posible, pero no basta con cambiar `DATABASE_URL`.** Este backend usa SQLAlchemy, relaciones y consultas relacionales, y Alembic para migraciones. MongoDB requiere rediseñar el acceso a datos y actualizar controladores, dependencias, pruebas y scripts. El tutorial siguiente describe el orden recomendado; no significa que el backend actual ya use MongoDB.

1. **Crea la base destino.** En MongoDB Atlas crea un proyecto y clúster, un usuario de base de datos con permisos mínimos y una base para desarrollo y otra para pruebas. Guarda el URI de conexión como secreto; no lo publiques ni lo agregues a Git.
2. **Diseña los documentos antes de importar.** Define las colecciones para usuarios, socios, autores, categorías, libros, préstamos y refresh tokens. Decide qué datos se embeben y cuáles se referencian; conserva las respuestas actuales de la API. Añade índices únicos para email normalizado e ISBN, y define cómo calcular disponibilidad, estados y multas.
3. **Refactoriza el backend.** Incorpora el driver oficial [PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/) y una capa de repositorios. Reemplaza sesiones y consultas de SQLAlchemy, joins, claves foráneas y migraciones Alembic por operaciones MongoDB, índices y validación de documentos. Actualiza `app/core/config.py`, pruebas, fixtures y el seed para usar una URI como `MONGODB_URI`. No elimines PostgreSQL/Alembic hasta que las pruebas del nuevo backend pasen.
4. **Respalda y migra los datos.** Antes de cambiar la aplicación, crea un respaldo PostgreSQL fuera de la carpeta del repositorio:

   ```powershell
   pg_dump -U postgres -d biblioteca -Fc -f "$env:USERPROFILE\biblioteca_pre_mongo.dump"
   ```

   Ajusta `-d` al nombre real de la base de desarrollo. Para la conversión puedes usar [MongoDB Relational Migrator](https://www.mongodb.com/docs/relational-migrator/) o un script ETL propio. Revisa la transformación de las relaciones, conserva los hashes de contraseña como texto y compara conteos y relaciones entre origen y destino.
5. **Valida y cambia el tráfico.** Detén temporalmente las escrituras o acuerda una ventana de mantenimiento, ejecuta la migración final, prueba registro/login, catálogo, préstamos, devoluciones, multas y reportes contra una base MongoDB de pruebas. Cambia la configuración de producción solo después de validar; conserva el respaldo PostgreSQL hasta confirmar el corte.
6. **Configura la conexión desde Vercel.** Añade `MONGODB_URI` y el nombre de la base como variables de entorno después de completar el refactor. Atlas filtra conexiones por IP; usa una salida de red estática admitida por tu plan de Vercel o aloja la API donde tengas una IP de salida fija. No abras el acceso de Atlas a `0.0.0.0/0` para evitar configurar la red.

La lista de IP de Atlas se explica en la [documentación de acceso de red](https://www.mongodb.com/docs/atlas/security/ip-access-list/); Vercel documenta sus [IP estáticas](https://vercel.com/docs/networking/static-ips), disponibles en planes Pro y Enterprise. Si no cuentas con salida estática, aloja la API en un servicio con IP de salida fija en vez de abrir Atlas a todas las IP. Para este proyecto, el camino de menor riesgo es desplegar primero la versión actual con PostgreSQL y planificar MongoDB como una migración separada.

## Integrantes

| Maria Fernanda Gonzalez Diaz | Aprendiz |

## Preparación del ZIP

Incluye `app/`, `alembic/`, `tests/` (solo archivos fuente), `frontend/`, `alembic.ini`, `requirements.txt`, `requirements-dev.txt`, `.env.example` y `README.md`.

Excluye `.env`, `.venv/`, `.git/`, `.vscode/`, `.idea/`, `frontend/.env`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`, `.pytest_cache/`, `.coverage`, archivos `*.pyc`, `*.db`, `*.log` y temporales. Antes de comprimir, revisa que `.env.example` siga usando únicamente los marcadores ficticios.
# BIBLIOTECA-FASTAPI-Maria-Gonzalez-Diaz
