/**
 * Session Controls Component
 * Session state is driven by POST /api/scalping/session responses.
 * No polling — WS events don't carry session state.
 */
import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { NgIf, NgClass, UpperCasePipe } from '@angular/common';
import { SessionApiService } from '../services/session-api.service';
import { ScalpingSession } from '../models/session.model';

@Component({
  selector: 'app-session-controls',
  standalone: true,
  imports: [NgIf, NgClass, UpperCasePipe],
  template: `
    <div class="session-controls">
      <h3>Scalping Session</h3>

      <div *ngIf="!session || session.status === 'idle'" class="start-section">
        <button class="btn btn-primary" (click)="startSession()">
          &#9654; Avvia Sessione
        </button>
      </div>

      <div *ngIf="session && session.status !== 'idle'" class="control-section">
        <span class="status-badge" [ngClass]="session.status">{{ session.status | uppercase }}</span>
        <span class="mode-badge">{{ session.mode | uppercase }}</span>

        <button *ngIf="session.status === 'running'" class="btn btn-pause" (click)="pauseSession()">
          &#9208; Pausa
        </button>
        <button *ngIf="session.status === 'paused'" class="btn btn-resume" (click)="resumeSession()">
          &#9654; Resume
        </button>
        <button class="btn btn-stop" (click)="stopSession()">
          &#9209; Stop
        </button>
      </div>
    </div>
  `,
  styles: [`
    .session-controls { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .start-section, .control-section { display: flex; gap: 8px; align-items: center; }
    .btn { padding: 6px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; border: none; }
    .btn-primary { background: var(--accent-primary, #F0B90B); color: #000; }
    .btn-pause { background: var(--accent-warning, #ffb74d); color: #000; }
    .btn-resume { background: var(--accent-success, #26a69a); color: #fff; }
    .btn-stop { background: var(--text-secondary); color: #fff; }
    .status-badge, .mode-badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; margin-right: 8px; }
    .status-badge.running { background: var(--accent-success, #26a69a); color: #fff; }
    .status-badge.paused { background: var(--accent-warning, #ffb74d); color: #000; }
    .mode-badge { background: var(--bg-elevated); color: var(--accent-primary, #F0B90B); }
  `],
})
export class SessionControlsComponent implements OnInit {
  session: ScalpingSession | null = null;

  constructor(
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.sessionApi.getStatus().subscribe({
      next: (data) => { this.session = data; this.cdr.detectChanges(); },
      error: () => {}
    });
  }

  startSession(): void {
    console.log('[SessionControls] Avvia Sessione clicked');
    this.sessionApi.start('paper').subscribe({
      next: (data: ScalpingSession) => {
        console.log('[SessionControls] Start OK:', data.status, data.session_id);
        this.session = data;
        this.cdr.detectChanges(); // Force change detection
      },
      error: (err: Error) => console.error('[SessionControls] FAILED:', err)
    });
  }

  stopSession(): void {
    if (!this.session) return;
    this.sessionApi.stop().subscribe({
      next: () => this.session = null,
      error: (err: Error) => console.error('Failed to stop session:', err)
    });
  }

  pauseSession(): void {
    if (!this.session) return;
    this.sessionApi.pause().subscribe({
      next: (data: ScalpingSession) => this.session = data,
      error: (err: Error) => console.error('Failed to pause session:', err)
    });
  }

  resumeSession(): void {
    if (!this.session) return;
    this.sessionApi.resume().subscribe({
      next: (data: ScalpingSession) => this.session = data,
      error: (err: Error) => console.error('Failed to resume session:', err)
    });
  }
}
