# Preparación de producción (no desplegada)

Se proporciona docker-compose.production.yml independiente. No combinarlo con docker-compose.yml: el archivo local usa reload, puertos de desarrollo y cuentas demo.

## Configuración

Copiar `.env.production.example` a `.env.production` y reemplazar contraseña, DATABASE_URL, SECRET_KEY y origen HTTPS real. La contraseña en DATABASE_URL debe codificar caracteres reservados de URL. El archivo real está ignorado por Git.

```powershell
# Generación local de una clave aleatoria, no compartir su salida.
python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose -f docker-compose.production.yml --env-file .env.production config --quiet
docker compose -f docker-compose.production.yml --env-file .env.production build
```

El backend rechaza claves cortas/de ejemplo, CORS comodín y exposición de tokens en producción. Solo la web publica un puerto, ligado por defecto a 127.0.0.1:8080. PostgreSQL y FastAPI quedan en la red de Compose. Nginx sirve Angular, resuelve rutas SPA y reenvía /api/ al backend. Angular usa el origen actual también para imágenes del vestidor.

El arranque aplica migraciones y carga únicamente roles (`seed --roles-only`), sin cuentas demo. El seed completo se rechaza con ENVIRONMENT=production. El volumen production_data y el nombre de proyecto vestidor-production separan los datos de desarrollo.

## Ejecución futura

No se ejecutó el siguiente comando durante el cierre:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production up -d
```

Configurar terminación TLS externa hacia 127.0.0.1:8080 antes de exponer la aplicación. Definir dominio, copias de seguridad y restauración de PostgreSQL, registros y supervisión. Respaldar la base antes de actualizar migraciones. `down` conserva el volumen; `down -v` elimina datos y no forma parte del procedimiento.

Para crear el primer administrador, registrar una cuenta propia y promoverla mediante una sesión administrativa controlada de base de datos, verificando el correo y el ID antes del UPDATE. No cargar usuarios demo en producción. La gestión posterior se realiza desde Usuarios.

## Limitaciones que impiden una tienda pública completa

- No hay pasarela real: aprobar/rechazar pagos simulados devuelve 403 en producción. La venta presencial registra un pago declarado; no verifica cobros externos.
- Recuperación: falta proveedor de correo/transporte para entregar el token sin exponerlo. No activar EXPOSE_RESET_TOKEN como solución.
- Falta validar TLS y la operación en el servidor final, así como restaurar un respaldo de prueba.
- Resolver vulnerabilidades de dependencias registradas en npm-audit.json antes de exposición pública; npm propone cambios mayores de Angular/CLI.
- El vestidor mantiene el alcance MVP existente.

No se añadieron servicios externos ni se cambió la arquitectura de la aplicación para cubrir estas limitaciones.
