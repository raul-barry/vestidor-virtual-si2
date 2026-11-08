import { Component } from '@angular/core';
import { DashboardComponent } from '../dashboard/dashboard.component';
import { AiReportPanelComponent } from './ai-report-panel.component';
import { BranchComparisonComponent } from './branch-comparison.component';

@Component({
  selector: 'app-admin-reports',
  standalone: true,
  imports: [DashboardComponent, AiReportPanelComponent, BranchComparisonComponent],
  template: '<app-admin-dashboard /><app-ai-report-panel /><app-branch-comparison />',
})
export class ReportsComponent {}
