import { Component } from '@angular/core';
import { DashboardComponent } from '../dashboard/dashboard.component';
@Component({selector:'app-admin-reports',standalone:true,imports:[DashboardComponent],template:'<app-admin-dashboard />'})
export class ReportsComponent {}
