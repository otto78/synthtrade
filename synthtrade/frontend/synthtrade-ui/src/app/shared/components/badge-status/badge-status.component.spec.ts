import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BadgeStatusComponent } from './badge-status.component';

describe('BadgeStatusComponent', () => {
  let fixture: ComponentFixture<BadgeStatusComponent>;

  function create(status: string) {
    fixture = TestBed.createComponent(BadgeStatusComponent);
    fixture.componentRef.setInput('status', status);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [BadgeStatusComponent] }));

  it('should render status text', () => {
    const el = create('ACTIVE');
    expect(el.querySelector('.badge')?.textContent).toBe('ACTIVE');
  });

  it('should apply badge--active for ACTIVE', () => {
    const el = create('ACTIVE');
    expect(el.querySelector('.badge')?.classList).toContain('badge--active');
  });

  it('should apply badge--active for APPROVED', () => {
    const el = create('APPROVED');
    expect(el.querySelector('.badge')?.classList).toContain('badge--active');
  });

  it('should apply badge--pending for PENDING', () => {
    const el = create('PENDING');
    expect(el.querySelector('.badge')?.classList).toContain('badge--pending');
  });

  it('should apply badge--rejected for REJECTED', () => {
    const el = create('REJECTED');
    expect(el.querySelector('.badge')?.classList).toContain('badge--rejected');
  });

  it('should apply badge--rejected for EXPIRED', () => {
    const el = create('EXPIRED');
    expect(el.querySelector('.badge')?.classList).toContain('badge--rejected');
  });
});
