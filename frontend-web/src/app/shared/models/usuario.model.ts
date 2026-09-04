export interface Usuario {
  id_usuario: number;
  nombres?: string;
  apellidos?: string;
  correo: string;
  telefono?: string | null;
  rol?: string;
}
