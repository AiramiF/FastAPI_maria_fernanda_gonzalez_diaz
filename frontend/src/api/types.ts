export type Role = "admin" | "bibliotecario" | "socio";

export interface User {
  id: number;
  email: string;
  nombre: string;
  rol: Role;
  activo: boolean;
  socio_id: number | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface Author {
  id: number;
  nombre: string;
  nacionalidad?: string | null;
  anio_nacimiento?: number | null;
}

export interface Category {
  id: number;
  nombre: string;
  descripcion?: string | null;
}

export interface Book {
  id: number;
  titulo: string;
  isbn: string;
  anio_publicacion: number;
  ejemplares: number;
  disponibles: number;
  portada_url: string | null;
  autor: { id: number; nombre: string };
  categorias: Array<{ id: number; nombre: string }>;
}

export interface Member {
  id: number;
  nombre: string;
  email: string;
  telefono?: string | null;
  activo?: boolean;
}

export interface Loan {
  id: number;
  libro_id: number;
  socio_id: number;
  fecha_prestamo: string;
  fecha_limite: string;
  fecha_devolucion: string | null;
  multa: number;
  multa_pagada: boolean;
  estado: "activo" | "vencido" | "devuelto";
  libro: { id: number; titulo: string };
  socio: { id: number; nombre: string; email: string };
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface ReportSummary {
  total_libros: number;
  total_ejemplares: number;
  prestados: number;
  socios_activos: number;
  vencidos: number;
  multas: number;
}

export interface StaffUser extends User {}

export type QueryValue = string | number | boolean | undefined | null;
