import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginPage } from './login.page';
import { AuthService } from '../../core/services/auth.service';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('LoginPage', () => {
  let fixture: ComponentFixture<LoginPage>;
  let el: HTMLElement;
  let authService: jest.Mocked<AuthService>;
  let router: jest.Mocked<Router>;

  beforeEach(async () => {
    authService = {
      login: jest.fn().mockReturnValue(of({ access_token: 'token' })),
    } as any;
    router = { navigate: jest.fn() } as any;

    await TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should render login form', () => {
    expect(el.querySelector('form')).toBeTruthy();
    expect(el.querySelector('input[type="password"]')).toBeTruthy();
    expect(el.querySelector('button[type="submit"]')).toBeTruthy();
  });

  it('should disable submit button when form is invalid', () => {
    const btn = el.querySelector('button[type="submit"]') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('should enable submit button when password is entered', () => {
    const input = el.querySelector('input[type="password"]') as HTMLInputElement;
    input.value = 'test123';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    const btn = el.querySelector('button[type="submit"]') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it('should call authService.login on submit', () => {
    const input = el.querySelector('input[type="password"]') as HTMLInputElement;
    input.value = 'test123';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    (el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    expect(authService.login).toHaveBeenCalledWith('test123');
  });

  it('should navigate to /dashboard on successful login', async () => {
    const input = el.querySelector('input[type="password"]') as HTMLInputElement;
    input.value = 'test123';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    (el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });

  it('should show error message on 401', async () => {
    authService.login.mockReturnValue(throwError(() => ({ status: 401 })));
    const input = el.querySelector('input[type="password"]') as HTMLInputElement;
    input.value = 'wrong';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    (el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(el.querySelector('.error')?.textContent).toContain('Password errata');
  });

  it('should show spinner during loading', () => {
    fixture.componentInstance.loading.set(true);
    fixture.detectChanges();
    expect(el.querySelector('.spinner')).toBeTruthy();
  });
});
