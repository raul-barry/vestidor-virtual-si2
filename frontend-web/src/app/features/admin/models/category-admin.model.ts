export interface Category {
  id_categoria: number;
  nombre: string;
  descripcion: string | null;
  estado: string;
}
export interface AdminCategory extends Category {}