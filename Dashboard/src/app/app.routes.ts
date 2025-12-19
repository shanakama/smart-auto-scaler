import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { PodsComponent } from './components/pods/pods.component';
import { DecisionsComponent } from './components/decisions/decisions.component';
import { ConfigComponent } from './components/config/config.component';
import { LoginComponent } from './components/login/login.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'pods', component: PodsComponent, canActivate: [authGuard] },
  { path: 'decisions', component: DecisionsComponent, canActivate: [authGuard] },
  { path: 'config', component: ConfigComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: '/dashboard' }
];
