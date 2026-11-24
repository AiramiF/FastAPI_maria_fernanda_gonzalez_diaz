# Biblioteca

Aplicación para explorar y administrar un catálogo bibliotecario, socios, préstamos, multas y reportes.

**Autora:** Maria Fernanda Gonzalez Diaz

**Programa:** ADSO, aprendiz — ficha 3230935

**Institución:** SENA

## Arquitectura

```text
frontend/                 SPA React + TypeScript + Vite
  src/api/                Cliente HTTP y tipos de la API
  src/auth/               Sesión y protección de rutas por rol
  src/components/         Componentes reutilizables
  src/pages/              Catálogo, cuenta y panel de gestión
app/
  main.py                 Aplicación FastAPI, middleware y routers
  routes/                 Rutas HTTP bajo /api/v1
  controllers/            Reglas de negocio y consultas
  schemas/                Validación y serialización Pydantic
  models/                 Tipos de documentos MongoDB
  core/                   Ajustes, repositorio, seguridad y servicios externos
  scripts/                Seed y creación interactiva de administrador
tests/                    Pruebas API sobre repositorio simulado en memoria
```

La API utiliza las colecciones `usuarios`, `refresh_tokens`, `autores`, `categorias`, `libros`, `socios`, `prestamos` y `multas`. `Repository` es la interfaz común: utiliza MongoDB Atlas cuando está accesible o `mongomock` en memoria si no hay URI, falla el ping o se ejecutan pruebas. El repositorio simulado no persiste datos al detener el proceso. El estado activo aparece en logs y en `GET /api/v1/health` (`database: "mongodb"` o `"simulada"`). Los datos de la base anterior no se convierten automáticamente; respalda y transforma los datos por separado si necesitas conservarlos.

## Tecnologías e integraciones

- **API:** Python, FastAPI, Pydantic, PyMongo, JWT, Argon2 (`pwdlib`) y SlowAPI.
- **Interfaz:** React 18, TypeScript, Vite y React Router.
- **MongoDB Atlas:** principal almacenamiento persistente; conexión con `MONGODB_URI`, timeout de selección de servidor de 3 segundos e índices únicos.
- **Modo simulado:** `mongomock`, con las mismas colecciones e interfaz de repositorio; incluye usuarios demo. Es temporal, no es un respaldo persistente ni debe usarse como base de producción.
- **Cloudinary:** almacenamiento opcional de portadas.
- **GitHub:** remoto `origin` ya apunta a `AiramiF/FastAPI_maria_fernanda_gonzalez_diaz`.
- **Vercel:** el frontend cuenta con rewrite SPA. La API se despliega por separado; no hay una URL de API de producción incluida en el repositorio.

## Funcionalidades y permisos

- Lectura pública del catálogo paginado de libros, autores y categorías.
- Registro, login, refresh/logout, perfil y cambio de contraseña.
- Roles `socio`, `bibliotecario` y `admin`; gestión del catálogo, socios, préstamos, usuarios y reportes según permisos.
- Préstamos, devoluciones, disponibilidad, multas por retraso y pagos.
- Carga, reemplazo y eliminación de portadas en Cloudinary.
- Access y refresh JWT, hash Argon2, rate limit para login/registro y encabezado `X-Request-ID`.

Las rutas, parámetros y esquemas se pueden consultar en `/docs` si `ENVIRONMENT` no es `prod`.

## Ejecutar en local (Windows / PowerShell)

Requisitos: Python 3.12+, Node.js/npm. MongoDB Atlas es opcional: sin URI o si no está accesible, el backend usa el modo simulado.

1. Instala dependencias Python y crea tu archivo local de variables:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```

2. Completa `.env` localmente. Define al menos `SECRET_KEY` (aleatoria, de 32 caracteres o más); puedes generarla sin mostrar ningún archivo:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Para Atlas, configura `MONGODB_URI` y `MONGODB_DATABASE`. Si `MONGODB_URI` queda vacía, se activa el modo simulado. No incluyas secretos en Git.

3. En una terminal, inicia el backend desde la raíz:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   fastapi dev app/main.py
   ```

   API: `http://localhost:8000`; documentación: `http://localhost:8000/docs`; health: `http://localhost:8000/api/v1/health`.

4. En otra terminal, inicia el frontend:

   ```powershell
   Set-Location frontend
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   npm ci
   npm run dev
   ```

   Abre `http://localhost:3000`. El cliente usa `VITE_API_URL`; en local, `frontend/.env.example` apunta a `http://localhost:8000/api/v1`. Para detener los servicios, pulsa `Ctrl+C` en cada terminal.

### Datos demo

En modo simulado no productivo, la API carga en memoria las cuentas básicas y un catálogo mínimo al arrancar. Con Atlas configurado, ejecuta `python -m app.scripts.seed_demo` para guardar el catálogo demo y las cuentas en la base persistente. El script `crear_admin` también requiere Atlas:

| Usuario | Contraseña demo | Rol |
|---|---|---|
| `admin@biblioteca.com` | `Biblioteca2026` | Admin |
| `socio@biblioteca.com` | `Biblioteca2026` | Socio |

Son credenciales públicas solo para desarrollo. Cámbialas y no uses el seed en producción. Para crear un administrador propio ejecuta `python -m app.scripts.crear_admin`.

## Variables de entorno

`.env.example` contiene únicamente nombres de variables. Define los valores en tu `.env` local o en el panel del proveedor:

| Variable | Dónde / uso |
|---|---|
| `MONGODB_URI` | Backend; URI privada de Atlas. Vacía activa la simulación. |
| `MONGODB_DATABASE` | Backend; nombre de la base MongoDB. |
| `SECRET_KEY` | Backend; firma JWT, mínimo 32 caracteres aleatorios. |
| `ALGORITHM` | Backend; algoritmo JWT (por defecto `HS256`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | Vigencia de tokens. |
| `ENVIRONMENT` | `dev`, `test` o `prod`. |
| `CORS_ORIGINS` | Backend; arreglo JSON con los orígenes permitidos. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Backend; portadas opcionales. |
| `VITE_API_URL` | Frontend; URL base pública de la API con `/api/v1`. No es un secreto. |

En Render/Railway configura `CORS_ORIGINS` como JSON, por ejemplo `["https://TU-PROYECTO.vercel.app"]`, usando el dominio real de Vercel. No uses `*` junto con credenciales.

## Pruebas

Las pruebas fuerzan `ENVIRONMENT=test` y usan `mongomock`; no se conectan a Atlas ni necesitan credenciales de MongoDB:

```powershell
.\.venv\Scripts\Activate.ps1
$env:ENVIRONMENT = "test"
pytest -q
$env:ENVIRONMENT = "dev"
```

## Vercel: configuración exacta del frontend

En Vercel importa el repositorio de GitHub y configura:

- **Root Directory:** `frontend`
- **Framework Preset:** `Vite`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install` (o el valor predeterminado de Vercel)
- **Environment Variable:** `VITE_API_URL=https://<dominio-del-backend>/api/v1` para Production y Preview según corresponda.

El build se ejecuta al desplegar; después de cambiar `VITE_API_URL`, crea un nuevo deployment. `frontend/vercel.json` envía las rutas de React Router a `index.html`.

### Desplegar la API aparte

Una alternativa sencilla es **Render** (Web Service Python) o **Railway**. Configura el comando de inicio:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Configura en el proveedor `MONGODB_URI`, `MONGODB_DATABASE`, `SECRET_KEY`, `ENVIRONMENT=prod` y `CORS_ORIGINS`; añade las tres variables Cloudinary si usarás portadas. Permite en Atlas la conectividad de red del proveedor de backend. No uses el modo simulado como almacenamiento productivo: los datos se pierden al reiniciar. Luego actualiza `VITE_API_URL` en Vercel con el dominio real de la API.

**Sobre “unavailable”:** el código por sí solo no permite determinar el estado de un deployment concreto; harían falta su URL o los logs de Vercel. Si Vercel no publica la página, revisa el resultado del build y el deployment; el rewrite SPA incluido evita fallos al abrir rutas internas directamente. Si la página sí abre pero login/datos fallan, revisa que exista una API pública desplegada, que `VITE_API_URL` apunte a ella y que CORS permita el dominio de Vercel. El ejemplo de frontend local apunta a `localhost`, que no sirve para producción.

## Actualizar GitHub desde Git Bash

### Primera configuración

1. Abre Git Bash dentro de la carpeta del proyecto (también puedes abrir Git Bash desde el menú contextual de esa carpeta):

   ```bash
   cd "/c/Users/USUARIO/Documents/. SENA/LUIS JORGE/PROYECTO_FASTAPI_BIBLIOTECA"
   ```

2. Configura el nombre y correo que aparecerán en tus commits (usa tu correo de GitHub):

   ```bash
   git config --global user.name "Maria Fernanda Gonzalez Diaz"
   git config --global user.email "TU-CORREO-DE-GITHUB"
   git config --global --list
   ```

3. Comprueba el remoto:

   ```bash
   git remote -v
   ```

   Debe aparecer el repositorio `AiramiF/FastAPI_maria_fernanda_gonzalez_diaz`.

### En cada actualización

1. Revisa qué cambió:

   ```bash
   git status
   ```

2. Confirma que `.env` no aparezca en la lista de cambios. Comprueba además que Git lo ignora:

   ```bash
   git check-ignore -v .env
   ```

   Si `.env` aparece en `git status`, **detente y no lo agregues**. Si ya estaba versionado, quitarlo del índice no elimina tu copia local: `git rm --cached .env`; si contenía credenciales publicadas, cámbialas.

3. Añade los cambios revisados:

   ```bash
   git add .
   git status
   ```

   Revisa de nuevo la lista preparada; no continúes si aparece algún secreto.

4. Crea el commit:

   ```bash
   git commit -m "Descripción corta del cambio"
   ```

5. Comprueba la rama antes de subir:

   ```bash
   git branch
   ```

   Si la rama actual es `main`, sube los cambios:

   ```bash
   git push origin main
   ```

   Si usas otra rama, reemplaza `main` por ese nombre.

6. Si el push falla porque GitHub tiene cambios nuevos, integra primero la rama remota y vuelve a intentar:

   ```bash
   git pull origin main --rebase
   git push origin main
   ```

   Si hay conflictos, resuélvelos en los archivos indicados, ejecuta `git add <archivo>` y `git rebase --continue`; luego repite el push.

7. Abre el repositorio en GitHub y verifica el commit/archivos. En Vercel revisa **Deployments**. Al conectar el proyecto Vercel con GitHub, cada push a la rama configurada dispara un deployment; si no se configuró esa integración, no será automático.

**Resumen diario (3 comandos):**

```bash
git status
git add .
git commit -m "Descripción corta" && git push origin main
```

Antes del `git add .`, verifica siempre que `.env` no aparezca en los cambios.
