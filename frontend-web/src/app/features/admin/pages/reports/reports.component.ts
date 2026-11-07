import { Component } from '@angular/core';
import { DashboardComponent } from '../dashboard/dashboard.component';
import { AiReportPanelComponent } from './ai-report-panel.component';

@Component({
  selector: 'app-admin-reports',
  standalone: true,
  imports: [DashboardComponent, AiReportPanelComponent],
  template: '<app-admin-dashboard /><app-ai-report-panel />',
})
export class ReportsComponent {}
