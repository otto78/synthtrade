/**
 * Session Controls Component
 * Start/Stop/Paper mode toggle
 */

import { Component } from '@angular/core';

@Component({
  selector: 'app-session-controls',
  standalone: true,
  template: `
    <div class="session-controls">
      <h3>Session Controls</h3>

      <div class="control-group">
        <button class="btn btn-primary" (click)="startSession()">Start</button>
        <button class="btn btn-secondary" (click)="stopSession()">Stop</button>
        <button class="btn" [class.btn-success]="mode === 'paper'" [class.btn-warning]="mode === 'live'" (click)="toggleMode()">
          {{ mode === 'paper' ? 'Paper' : 'LIVE' }}
        </button>
      </div>

      <div class="status">
        <span class="dot" [class.running]="running"></span>
        <span>{{ running ? 'Running' : 'Stopped' }}</span>
      </div>
    </div>
  `,
  styles: [`
    .session-controls { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .control-group { display: flex; gap: 8px; margin-bottom: 12px; }
    .btn { padding: 6px 12px; border: 1px solid var(--border-default); border-radius: 4px; background: var(--bg-elevated); color: var(--text-primary); cursor: pointer; }
    .btn-primary { background: var(--accent-primary, #F0B90B); color: #000; border-color: var(--accent-primary); }
    .btn-secondary { background: var(--text-secondary); color: #000; }
    .status { display: flex; align-items: center; gap: 6px; font-size: 12px; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-secondary); }
    .dot.running { background: #26a69a; }
  `],
})
export class SessionControlsComponent {
  running = false;
  mode: 'paper' | 'live' = 'paper';

  startSession(): void {
    this.running = true;
  }

  stopSession(): void {
    this.running = false;
  }

  toggleMode(): void {
    this.mode = this.mode === 'paper' ? 'live' : 'paper';
  }
}