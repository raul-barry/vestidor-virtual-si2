# Vestidor Virtual

Monorepositorio base para una plataforma inteligente de comercio electronico de ropa masculina, preparada para incorporar vestidor virtual con realidad aumentada e inteligencia artificial.

## Tecnologias

- Frontend web: Angular 17, Angular Material y Tailwind CSS.
- Aplicacion movil: Flutter.
- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic y JWT.
- Datos: PostgreSQL 16.
- Entornos: Docker Compose.

## Estructura

```text
.
|-- backend/                 # API FastAPI por capas
|   |-- alembic/             # Configuracion y futuras migraciones ORM
|   |-- app/
|   |   |-- api/             # Rutas REST futuras
|   |   |-- core/            # Configuracion y seguridad
|   |   |-- database/        # Conexion y base ORM
|   |   |-- models/          # Modelos SQLAlchemy futuros
|   |   |-- repositories/    # Acceso a datos futuro
|   |   |-- schemas/         # Esquemas Pydantic futuros
|   |   |-- services/        # Logica de negocio futura
|   |   |-- main.py
|   |-- Dockerfile
|   `-- requirements.txt
|-- frontend-web/            # Aplicacion Angular 17
|   `-- src/app/
|       |-- core/            # Servicios, interceptores y guards futuros
|       |-- features/        # Modulos funcionales futuros
|       |-- layouts/         # Plantillas futuras
|       `-- shared/          # Componentes reutilizables futuros
|-- mobile/                  # Aplicacion Flutter
|   `-- lib/
|       |-- core/            # Configuracion general
|       |-- features/        # Modulos funcionales futuros
|       |-- models/          # Modelos de datos futuros
|       `-- services/        # Cliente API base
|-- database/scripts/        # Scripts SQL de migracion futuros
`-- docker-compose.yml
```

## Ejecutar el ambiente

1. Cree el archivo de variables de entorno: `Copy-Item .env.example .env`.
2. Inicie los servicios: `docker compose up --build`.
3. Acceda a la aplicacion web en `http://localhost:4200` y a la documentacion de FastAPI en `http://localhost:8000/docs`.

Para detener los servicios, ejecute `docker compose down`. Los datos de PostgreSQL permanecen en el volumen `postgres_data`.

## Desarrollo local

- Backend: copie `backend/.env.example` como `backend/.env`, instale `pip install -r backend/requirements.txt` con Python 3.12 y ejecute `uvicorn app.main:app --reload` desde `backend`.
- Frontend: ejecute `npm install` y `npm start` desde `frontend-web`.
- Mobile: ejecute `flutter pub get` y luego `flutter run --dart-define=API_BASE_URL=http://<host>:8000` desde `mobile`.

## Datos iniciales

Después de aplicar las migraciones, cargue los roles maestros requeridos por el registro de clientes:

```powershell
cd backend
alembic upgrade head
python -m app.database.seed
```

El seed es idempotente: crea solamente los roles que no existen (`CLIENTE`, `ADMINISTRADOR`, `CAJERO` y `ENCARGADO_SUCURSAL`).

Con Docker Compose, ejecute:

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.database.seed
```
