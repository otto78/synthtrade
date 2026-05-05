import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ConfirmDialogComponent } from './confirm-dialog.component';

describe('ConfirmDialogComponent', () => {
  let fixture: ComponentFixture<ConfirmDialogComponent>;
  let el: HTMLElement;

  function create(visible: boolean, message = 'Sei sicuro?') {
    fixture = TestBed.createComponent(ConfirmDialogComponent);
    fixture.componentRef.setInput('visible', visible);
    fixture.componentRef.setInput('message', message);
    fixture.detectChanges();
    el = fixture.nativeElement;
    return el;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [ConfirmDialogComponent] }));

  it('should not render when visible=false', () => {
    create(false);
    expect(el.querySelector('.modal-overlay')).toBeNull();
  });

  it('should render when visible=true', () => {
    create(true);
    expect(el.querySelector('.modal-overlay')).toBeTruthy();
    expect(el.querySelector('p')?.textContent).toBe('Sei sicuro?');
  });

  it('should emit confirmed on confirm button click', () => {
    create(true);
    const confirmed = jest.fn();
    fixture.componentInstance.confirmed.subscribe(confirmed);
    (el.querySelector('.btn-danger') as HTMLElement).click();
    expect(confirmed).toHaveBeenCalled();
  });

  it('should emit cancelled on cancel button click', () => {
    create(true);
    const cancelled = jest.fn();
    fixture.componentInstance.cancelled.subscribe(cancelled);
    (el.querySelector('.btn-ghost') as HTMLElement).click();
    expect(cancelled).toHaveBeenCalled();
  });

  it('should emit cancelled on Escape keydown', () => {
    create(true);
    const cancelled = jest.fn();
    fixture.componentInstance.cancelled.subscribe(cancelled);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(cancelled).toHaveBeenCalled();
  });
});
