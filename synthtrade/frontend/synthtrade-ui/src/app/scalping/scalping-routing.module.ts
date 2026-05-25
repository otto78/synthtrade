/**
 * Scalping Routing Module
 */

import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ScalpingDashboardComponent } from './components/scalping-dashboard.component';

const routes: Routes = [
  { path: '', component: ScalpingDashboardComponent },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class ScalpingRoutingModule {}