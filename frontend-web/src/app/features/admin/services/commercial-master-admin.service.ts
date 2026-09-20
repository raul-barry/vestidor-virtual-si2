import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { Collection, CollectionProduct, CollectionRequest, LogicalState, Supplier, SupplierRequest } from '../models/commercial-master.model';

@Injectable({ providedIn: 'root' })
export class CommercialMasterAdminService {
  constructor(private api: ApiService) {}

  listSuppliers(): Observable<Supplier[]> { return this.api.get<Supplier[]>('/api/admin/suppliers'); }
  createSupplier(request: SupplierRequest): Observable<Supplier> { return this.api.post<Supplier>('/api/admin/suppliers', request); }
  updateSupplier(id: number, request: SupplierRequest): Observable<Supplier> { return this.api.put<Supplier>(`/api/admin/suppliers/${id}`, request); }
  setSupplierState(id: number, estado: LogicalState): Observable<Supplier> { return this.api.patch<Supplier>(`/api/admin/suppliers/${id}/status`, { estado }); }

  listCollections(): Observable<Collection[]> { return this.api.get<Collection[]>('/api/admin/collections'); }
  createCollection(request: CollectionRequest): Observable<Collection> { return this.api.post<Collection>('/api/admin/collections', request); }
  updateCollection(id: number, request: CollectionRequest): Observable<Collection> { return this.api.put<Collection>(`/api/admin/collections/${id}`, request); }
  setCollectionState(id: number, estado: LogicalState): Observable<Collection> { return this.api.patch<Collection>(`/api/admin/collections/${id}/status`, { estado }); }
  listCollectionProducts(id: number): Observable<CollectionProduct[]> { return this.api.get<CollectionProduct[]>(`/api/admin/collections/${id}/products`); }
  listProducts(): Observable<CollectionProduct[]> { return this.api.get<CollectionProduct[]>('/api/commerce/products'); }
  associateProduct(collectionId: number, productId: number): Observable<CollectionProduct> { return this.api.put<CollectionProduct>(`/api/admin/collections/${collectionId}/products/${productId}`, {}); }
  removeProduct(collectionId: number, productId: number): Observable<void> { return this.api.delete<void>(`/api/admin/collections/${collectionId}/products/${productId}`); }
}
