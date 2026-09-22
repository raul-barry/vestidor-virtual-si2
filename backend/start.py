import os
import sys
import subprocess
import uvicorn

# Configurar stdout y stderr sin buffer para ver logs inmediatamente en Render
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


def run():
    print("=" * 50)
    print("=== [INICIANDO BACKEND VESTIDOR VIRTUAL] ===")
    print("=" * 50)

    # 1. Ejecutar migraciones Alembic
    print("--> Paso 1/3: Aplicando migraciones de base de datos con Alembic...")
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
        print("--> [OK] Migraciones aplicadas exitosamente.")
    except Exception as e:
        print(f"--> [ERROR] Error en migraciones: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Ejecutar seed de catálogo inicial
    print("--> Paso 2/3: Ejecutando seed de datos iniciales...")
    try:
        subprocess.run([sys.executable, "-m", "app.database.seed"], check=True)
        print("--> [OK] Datos iniciales cargados exitosamente.")
    except Exception as e:
        print(f"--> [ADVERTENCIA] Error al ejecutar seed: {e}", file=sys.stderr)

    # 3. Iniciar servidor Uvicorn en 0.0.0.0 y puerto asignado por Render
    port = int(os.environ.get("PORT", 10000))
    host = "0.0.0.0"
    print(f"--> Paso 3/3: Iniciando servidor Uvicorn en {host}:{port}...")
    sys.stdout.flush()

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    run()
