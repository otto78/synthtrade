import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StatCardComponent } from './stat-card.component';

describe('StatCardComponent', () => {
  let fixture: ComponentFixture<StatCardComponent>;

  function create(inputs: { label: string; value: string; delta?: number | null; loading?: boolean }) {
    fixture = TestBed.createComponent(StatCardComponent);
    fixture.componentRef.setInput('label', inputs.label);
    fixture.componentRef.setInput('value', inputs.value);
    if (inputs.delta !== undefined) fixture.componentRef.setInput('delta', inputs.delta);
    if (inputs.loading !== undefined) fixture.componentRef.setInput('loading', inputs.loading);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [StatCardComponent] }));

  it('should render label and value', () => {
    const el = create({ label: 'Balance', value: '$1,000' });
    expect(el.querySelector('.label')?.textContent).toBe('Balance');
    expect(el.querySelector('.value')?.textContent?.trim()).toBe('$1,000');
  });

  it('should show delta when provided', () => {
    const el = create({ label: 'PnL', value: '+5%', delta: 2.5 });
    expect(el.querySelector('.delta')).toBeTruthy();
    expect(el.querySelector('.delta')?.textContent).toContain('+');
  });

  it('should not render delta when null', () => {
    const el = create({ label: 'PnL', value: '0', delta: null });
    expect(el.querySelector('.delta')).toBeNull();
  });

  it('should show skeleton when loading=true', () => {
    const el = create({ label: 'X', value: 'Y', loading: true });
    expect(el.querySelector('.skeleton')).toBeTruthy();
  });
});
