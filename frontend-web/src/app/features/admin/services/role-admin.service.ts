import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminPermission, AdminRole, RoleRequest } from '../models/role-admin.model';
@Injectable({providedIn:'root'})
export class RoleAdminService {constructor(private api:ApiService){}list():Observable<AdminRole[]>{return this.api.get('/api/admin/roles')}permissions():Observable<AdminPermission[]>{return this.api.get('/api/admin/roles/permissions')}create(data:RoleRequest):Observable<AdminRole>{return this.api.post('/api/admin/roles',data)}update(id:number,data:RoleRequest):Observable<AdminRole>{return this.api.put(`/api/admin/roles/${id}`,data)}toggle(id:number):Observable<AdminRole>{return this.api.patch(`/api/admin/roles/${id}/toggle-status`,{})}}
