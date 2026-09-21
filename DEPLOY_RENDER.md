# Guía de Despliegue en Render Cloud: Vestidor Virtual

Esta guía detalla los pasos para subir y ejecutar todo el proyecto **Vestidor Virtual** (Base de Datos PostgreSQL, Backend FastAPI y Frontend Web Angular) en la plataforma **Render** ([render.com](https://render.com)).

---

## Servicios que se desplegarán

1. **Base de Datos**: PostgreSQL 16 (Managed Database en Render o externa).
2. **Backend API**: Servicio Web Python 3.12 con FastAPI, migraciones automáticas Alembic y carga de catálogo inicial (seed).
3. **Frontend Web**: Sitio Estático (Static Site) con Angular 17 alojado en CDN global (completamente gratuito e ilimitado en Render).

---

## Paso Previo Obligatorio: Subir los cambios a GitHub

Como Render se sincroniza automáticamente con tu repositorio de GitHub, primero guarda y sube las configuraciones que acabamos de agregar:

```powershell
git add .
git commit -m "feat: preparar configuracion para despliegue en Render Cloud"
git push origin main
```

---

## Opción A: Despliegue Automático con Blueprint (Recomendado - 1 Clic)

El repositorio incluye un archivo [`render.yaml`](./render.yaml) que define la base de datos, el backend y el frontend de forma automatizada.

1. Inicia sesión en [Render Dashboard](https://dashboard.render.com/).
2. Haz clic en el botón **"New +"** (arriba a la derecha) y selecciona **"Blueprint"**.
3. Conecta tu cuenta de GitHub y selecciona el repositorio `vestidor-virtual-si2`.
4. Render detectará automáticamente el archivo `render.yaml` y listará los 3 recursos a crear:
   - Base de datos: `vestidor-db`
   - Backend: `vestidor-virtual-backend`
   - Frontend: `vestidor-virtual-frontend`
5. Haz clic en **"Apply"**.
6. Render comenzará a aprovisionar la base de datos, compilar el backend y generar el frontend.

---

## Opción B: Despliegue Manual (Paso a Paso en el Dashboard)

Si prefieres configurar cada servicio manualmente desde el panel de Render, sigue estos pasos:

### 1. Crear la Base de Datos PostgreSQL
1. En Render Dashboard, haz clic en **New +** -> **PostgreSQL**.
2. Completa los campos:
   - **Name**: `vestidor-db`
   - **Database**: `vestidor_virtual`
   - **User**: `vestidor_user`
   - **Region**: Elige la más cercana (ej. `Oregon (US West)` o `Ohio (US East)`).
   - **Plan**: `Free`.
3. Haz clic en **Create Database**.
4. Una vez creada, en la sección de **Connections**, copia la **Internal Database URL** (se utilizará en el Backend).

---

### 2. Crear el Servicio Web del Backend (FastAPI)
1. En Render Dashboard, haz clic en **New +** -> **Web Service**.
2. Selecciona tu repositorio de GitHub `vestidor-virtual-si2`.
3. Configura los siguientes campos:
   - **Name**: `vestidor-virtual-backend`
   - **Language / Runtime**: `Python 3`
   - **Region**: La misma que la base de datos.
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**:
     ```bash
     alembic upgrade head && python -m app.database.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: `Free`
4. Despliega la pestaña **Advanced** y añade las siguientes **Environment Variables**:
   - `DATABASE_URL`: Pega la *Internal Database URL* de la base de datos creada en el paso 1.
   - `SECRET_KEY`: Genera una clave segura (ej. una cadena aleatoria larga).
   - `CORS_ORIGINS`: `*` (o la URL de tu frontend una vez creado).
   - `PYTHON_VERSION`: `3.12.2`
   - **Health Check Path**: `/health`
5. Haz clic en **Create Web Service**.
6. Copia la URL pública que Render le asigne a tu backend (ejemplo: `https://vestidor-virtual-backend.onrender.com`).

---

### 3. Crear el Sitio Estático del Frontend (Angular)
1. En Render Dashboard, haz clic en **New +** -> **Static Site**.
2. Selecciona tu repositorio de GitHub `vestidor-virtual-si2`.
3. Configura los siguientes campos:
   - **Name**: `vestidor-virtual-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend-web`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist/vestidor-virtual-web/browser`
4. En **Redirects / Rewrites** (para soportar el enrutamiento de Angular al recargar):
   - Haz clic en **Add Rule**.
   - **Type**: `Rewrite`
   - **Source**: `/*`
   - **Destination**: `/index.html`
5. En la sección **Environment Variables**, añade:
   - `API_URL`: La URL pública de tu backend (por ejemplo `https://vestidor-virtual-backend.onrender.com`).
6. Haz clic en **Create Static Site**.

---

## Cuentas de Prueba Precargadas (Seed Data)

El comando de arranque del backend ejecuta automáticamente el script de inicialización con las siguientes credenciales:

| Rol | Correo | Contraseña |
|---|---|---|
| **Administrador** | `admin@vestidor.local` | `Admin123!` |
| **Cliente** | `cliente@vestidor.local` | `Cliente123!` |

Además, se cargan automáticamente categorías de ropa, tallas, colores, sucursal central, productos con variantes y stock inicial.

---

## Notas Importantes sobre el Plan Gratuito de Render

1. **Suspensión por inactividad (Spin-down)**:
   - Los Web Services gratuitos de Render entran en suspensión tras 15 minutos sin recibir visitas.
   - Cuando vuelvas a ingresar a la web o a la API, Render levantará el contenedor nuevamente. Esto puede tardar entre **30 y 50 segundos** en la primera petición. Las peticiones subsiguientes responderán de inmediato.
2. **Duración de la base de datos gratuita de Render**:
   - Render ofrece su base de datos PostgreSQL gratuita durante 30 días.
   - **Recomendación para base de datos gratuita permanente**: Puedes crear una base de datos PostgreSQL gratuita en [Supabase](https://supabase.com) o [Neon](https://neon.tech) (ambas no tienen límite de 30 días) y simplemente colocar su URL en la variable de entorno `DATABASE_URL` del backend en Render.
