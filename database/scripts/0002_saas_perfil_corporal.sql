CREATE TABLE IF NOT EXISTS organizacion (id_organizacion SERIAL PRIMARY KEY, nombre VARCHAR(150) UNIQUE NOT NULL, estado VARCHAR(30) NOT NULL DEFAULT 'ACTIVA');
INSERT INTO organizacion(nombre) SELECT 'Fashion Store' WHERE NOT EXISTS (SELECT 1 FROM organizacion);
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS id_organizacion INTEGER REFERENCES organizacion(id_organizacion);
ALTER TABLE sucursal ADD COLUMN IF NOT EXISTS id_organizacion INTEGER REFERENCES organizacion(id_organizacion);
ALTER TABLE producto ADD COLUMN IF NOT EXISTS id_organizacion INTEGER REFERENCES organizacion(id_organizacion);
CREATE TABLE IF NOT EXISTS perfil_corporal (id_perfil_corporal SERIAL PRIMARY KEY, id_usuario INTEGER UNIQUE NOT NULL REFERENCES usuario(id_usuario), consentimiento BOOLEAN NOT NULL, altura_cm NUMERIC(6,2), peso_kg NUMERIC(6,2), pecho_cm NUMERIC(6,2), cintura_cm NUMERIC(6,2), cadera_cm NUMERIC(6,2), largo_pierna_cm NUMERIC(6,2), ancho_hombros_cm NUMERIC(6,2), foto_frontal VARCHAR(500), foto_posterior VARCHAR(500), foto_lateral_izquierda VARCHAR(500), foto_lateral_derecha VARCHAR(500));
UPDATE usuario SET id_organizacion=(SELECT id_organizacion FROM organizacion WHERE nombre='Fashion Store') WHERE id_organizacion IS NULL;
UPDATE sucursal SET id_organizacion=(SELECT id_organizacion FROM organizacion WHERE nombre='Fashion Store') WHERE id_organizacion IS NULL;
UPDATE producto SET id_organizacion=(SELECT id_organizacion FROM organizacion WHERE nombre='Fashion Store') WHERE id_organizacion IS NULL;
