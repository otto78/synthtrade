import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TopbarComponent } from './topbar.component';
import { AuthService } from '../../core/services/auth.service';
import { BehaviorSubject } from 'rxjs';

describe('TopbarComponent', () => {
  let fixture: ComponentFixture<TopbarComponent>;
  let el: HTMLElement;
  let authService: jest.Mocked<AuthService>;

  beforeEach(async () => {
    authService = {
      currentUser$: new BehaviorSubject<string | null>('admin'),
      logout: jest.fn(),
    } as any;

    await TestBed.configureTestingModule({
      imports: [TopbarComponent],
      providers: [{ provide: AuthService, useValue: authService }],
    }).compileComponents();

    fixture = TestBed.createComponent(TopbarComponent);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should display username from AuthService', () => {
    expect(el.querySelector('.username')?.textContent?.trim()).toBe('admin');
  });

  it('should call logout on button click', () => {
    (el.querySelector('.btn-logout') as HTMLElement).click();
    expect(authService.logout).toHaveBeenCalled();
  });
});
