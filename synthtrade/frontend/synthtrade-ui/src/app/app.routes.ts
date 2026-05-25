import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { noAuthGuard } from './core/guards/no-auth.guard';
import { AppShellComponent } from './layout/app-shell/app-shell.component';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [noAuthGuard],
    loadComponent: () => import('./pages/login/login.page').then(m => m.LoginPage),
  },
  {
    path: '',
    component: AppShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./pages/dashboard/dashboard.page').then(m => m.DashboardPage),
      },
      {
        path: 'strategies',
        loadComponent: () => import('./pages/strategies/strategies.page').then(m => m.StrategiesPage),
      },
      {
        path: 'active-trade',
        loadComponent: () => import('./pages/active-trade/active-trade.page').then(m => m.ActiveTradePage),
      },
      {
        path: 'logs',
        loadComponent: () => import('./pages/logs/logs.page').then(m => m.LogsPage),
      },
      {
        path: 'llm-models',
        loadComponent: () => import('./pages/llm-models/llm-models.page').then(m => m.LLMModelsPage),
      },
      {
        path: 'scalping',
        loadChildren: () => import('./scalping/scalping.module').then(m => m.ScalpingModule),
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
