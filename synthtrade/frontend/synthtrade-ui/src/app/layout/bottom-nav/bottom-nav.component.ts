import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { NAV_ITEMS } from '../nav-items';

@Component({
  selector: 'app-bottom-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nav class="bottom-nav">
      @for (item of navItems; track item.route) {
        <a [routerLink]="item.route" routerLinkActive="bottom-nav-item--active" class="bottom-nav-item">
          <span class="bottom-nav-icon">{{ item.icon }}</span>
          <span class="bottom-nav-label">{{ item.label }}</span>
        </a>
      }
    </nav>
  `,
  styles: [`
    .bottom-nav {
      display: flex;
      position: fixed;
      bottom: 0; left: 0; right: 0;
      height: 60px;
      background: var(--bg-surface, #0D1117);
      border-top: 1px solid var(--border-default, rgba(234,236,239,0.08));
      z-index: 100;
      padding-bottom: env(safe-area-inset-bottom);
    }
    .bottom-nav-item {
      flex: 1;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      gap: 2px;
      color: var(--text-secondary, #848E9C);
      text-decoration: none;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.3px;
    }
    .bottom-nav-icon { font-size: 18px; line-height: 1; }
    .bottom-nav-item--active {
      color: var(--accent-primary, #F0B90B);
    }
  `]
})
export class BottomNavComponent {
  readonly navItems = NAV_ITEMS;
}
