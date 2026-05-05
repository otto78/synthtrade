import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { NgClass } from '@angular/common';

const NAV_ITEMS = [
  { label: 'Dashboard',    icon: '⬡', route: '/dashboard' },
  { label: 'Strategies',   icon: '◈', route: '/strategies' },
  { label: 'Active Trade', icon: '◉', route: '/active-trade' },
  { label: 'Logs',         icon: '≡', route: '/logs' },
];

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nav class="sidebar" [ngClass]="{ 'sidebar--collapsed': collapsed() }">
      <div class="sidebar-header">
        @if (!collapsed()) {
          <span class="logo">SynthTrade</span>
        }
        <button class="sidebar-toggle" (click)="toggle()" aria-label="Toggle sidebar">
          {{ collapsed() ? '›' : '‹' }}
        </button>
      </div>

      <ul class="nav-list">
        @for (item of navItems; track item.route) {
          <li class="nav-item">
            <a [routerLink]="item.route" routerLinkActive="nav-item--active" class="nav-link">
              <span class="nav-icon">{{ item.icon }}</span>
              @if (!collapsed()) {
                <span class="nav-label">{{ item.label }}</span>
              }
            </a>
          </li>
        }
      </ul>
    </nav>
  `,
  styles: [`
    .sidebar {
      width: 240px; height: 100vh; background: var(--bg-surface, #0D1117);
      display: flex; flex-direction: column; transition: width 0.2s ease;
      border-right: 1px solid var(--border-default, rgba(234,236,239,0.06));
      flex-shrink: 0;
    }
    .sidebar--collapsed { width: 56px; }
    .sidebar-header {
      height: 56px; display: flex; align-items: center; justify-content: space-between;
      padding: 0 12px; border-bottom: 1px solid var(--border-default, rgba(234,236,239,0.06));
    }
    .logo { font-family: 'Chakra Petch', sans-serif; font-size: 14px; font-weight: 700; color: var(--accent-primary, #F0B90B); }
    .sidebar-toggle {
      background: none; border: none; color: var(--text-secondary, #848E9C);
      cursor: pointer; font-size: 18px; padding: 4px; line-height: 1;
    }
    .nav-list { list-style: none; padding: 8px 0; margin: 0; }
    .nav-link {
      display: flex; align-items: center; gap: 12px; padding: 10px 16px;
      color: var(--text-secondary, #848E9C); text-decoration: none; font-size: 13px;
      transition: all 0.2s ease; border-left: 2px solid transparent;
    }
    .nav-link:hover, .nav-item--active .nav-link, a.nav-item--active {
      color: var(--text-primary, #EAECEF);
      background: linear-gradient(90deg, var(--accent-glow, rgba(240,185,11,0.15)), transparent);
      border-left-color: var(--accent-primary, #F0B90B);
    }
    .nav-icon { font-size: 16px; flex-shrink: 0; }
  `]
})
export class SidebarComponent {
  readonly navItems = NAV_ITEMS;
  collapsed = signal(false);

  toggle(): void {
    this.collapsed.update(v => !v);
  }
}
