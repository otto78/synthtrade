import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { TopbarComponent } from '../topbar/topbar.component';
import { BottomNavComponent } from '../bottom-nav/bottom-nav.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent, TopbarComponent, BottomNavComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="shell">
      <app-sidebar />
      <div class="main">
        <app-topbar />
        <main class="content">
          <router-outlet />
        </main>
      </div>
      <app-bottom-nav />
    </div>
  `,
  styles: [`
    .shell { display: flex; height: 100vh; overflow: hidden; background: var(--bg-base, #07090C); }
    .main { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
    .content { flex: 1; overflow-y: auto; padding: 24px; }

    /* Desktop: bottom nav nascosta */
    app-bottom-nav { display: none; }

    /* Mobile: niente sidebar, navigazione in basso */
    @media (max-width: 768px) {
      app-sidebar { display: none; }
      app-bottom-nav { display: block; }
      .content { padding: 12px; padding-bottom: calc(72px + env(safe-area-inset-bottom)); }
    }
  `]
})
export class AppShellComponent {}
