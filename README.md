# Vestidor Virtual SI2

Plataforma académica funcional: FastAPI/PostgreSQL, Angular 17 y Flutter. Incluye catálogo, administración, inventario, compra con pago simulado, reservas, recomendaciones y vestidor virtual MVP.

## Inicio local para demostración

```powershell
Copy-Item .env.example .env # Solo si no existe; conservar variables locales existentes.
docker compose up -d --build
```

Web: http://localhost:4200 · API: http://localhost:8000/docs · Salud: http://localhost:8000/health.
El backend aplica migraciones y ejecuta el seed de desarrollo. No borrar el volumen para reiniciar la aplicación.

| Rol | Correo | Contraseña de demostración |
|---|---|---|
| Administrador | admin@vestidor.local | Admin123! |
| Cliente | cliente@vestidor.local | Cliente123! |
| Encargado | encargado@vestidor.local | Encargado123! |
| Cajero | cajero@vestidor.local | Cajero123! |

El seed reutiliza registros existentes, crea productos, variantes, recursos de vestidor, inventario y asignaciones de sucursal. No restablece contraseñas ni repone stock de registros existentes.
Para asegurar pedidos y reservas visibles del cliente demo, desde backend ejecutar `python scripts/prepare_demo.py` con la API local arrancada. Usa endpoints actuales; omite la creación si ya hay registros. En una cuenta demo con carrito previo, la compra incluirá su contenido.

## Desarrollo y verificaciones

Backend (desde backend, Python 3.12 recomendado):

```powershell
pip install -r requirements.txt
# Configurar backend/.env a partir de backend/.env.example.
alembic upgrade head
python -m app.database.seed
uvicorn app.main:app --reload
python -m pytest
```

Angular (desde frontend-web):

```powershell
npm.cmd ci
npm.cmd start
npm.cmd run build
npm.cmd run test:ci
npm.cmd run test:visual
```

En Windows se usa npm.cmd si PowerShell bloquea npm.ps1. Las pruebas visuales requieren Chrome; permiten CHROME_BIN y generan imágenes en frontend-web/artifacts/visual. Usan datos simulados, no certifican la integración con PostgreSQL.

Flutter (desde mobile):

```powershell
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

10.0.2.2 corresponde al emulador Android. En un teléfono usar la IP LAN del equipo. La aplicación móvil está orientada a CLIENTE.

Prueba integral real (desde backend, solo entorno de desarrollo):

```powershell
$env:VV_E2E_BASE_URL='http://localhost:8000'
python -m pytest tests/test_live_journey.py -q
Remove-Item Env:VV_E2E_BASE_URL
```

Esta prueba crea registros con sufijo único y modifica stock; restaura las asignaciones de empleados. No ejecutarla contra producción.

## Documentación de cierre

- [Auditoría, matriz de casos, pruebas y pendientes](docs/CIERRE.md)
- [Guion de demostración y capturas](docs/DEMOSTRACION.md)
- [Preparación de producción, sin despliegue](docs/PRODUCCION.md)

Los pagos web/móvil son simulados en desarrollo. El vestidor es un MVP, no una garantía de ajuste físico ni una implementación completa de realidad aumentada. La recuperación genera tokens, pero todavía no dispone de envío de correo real.
