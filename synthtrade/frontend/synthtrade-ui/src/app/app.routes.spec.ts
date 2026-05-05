import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Location } from '@angular/common';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { TokenStorageService } from './core/services/token-storage.service';

describe('App Routing', () => {
  let router: Router;
  let location: Location;
  let tokenStorage: jest.Mocked<TokenStorageService>;

  beforeEach(async () => {
    tokenStorage = {
      getAccessToken: jest.fn().mockReturnValue(null),
      isTokenExpired: jest.fn().mockReturnValue(true),
    } as any;

    await TestBed.configureTestingModule({
      providers: [
        provideRouter(routes),
        { provide: TokenStorageService, useValue: tokenStorage },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    location = TestBed.inject(Location);
  });

  it('should redirect empty path to /login when not authenticated', async () => {
    tokenStorage.getAccessToken.mockReturnValue(null);
    await router.navigate(['']);
    expect(location.path()).toBe('/login');
  });

  it('should redirect wildcard to /login when not authenticated', async () => {
    tokenStorage.getAccessToken.mockReturnValue(null);
    await router.navigate(['/non-existent-route']);
    expect(location.path()).toBe('/login');
  });

  it('should redirect empty path to /dashboard when authenticated', async () => {
    tokenStorage.getAccessToken.mockReturnValue('valid-token');
    tokenStorage.isTokenExpired.mockReturnValue(false);
    await router.navigate(['']);
    expect(location.path()).toBe('/dashboard');
  });

  it('should redirect to /login when accessing protected route without token', async () => {
    tokenStorage.getAccessToken.mockReturnValue(null);
    await router.navigate(['/dashboard']);
    expect(location.path()).toBe('/login');
  });

  it('should allow access to /login without token', async () => {
    tokenStorage.getAccessToken.mockReturnValue(null);
    await router.navigate(['/login']);
    expect(location.path()).toBe('/login');
  });

  it('should redirect from /login to /dashboard when authenticated', async () => {
    tokenStorage.getAccessToken.mockReturnValue('valid-token');
    tokenStorage.isTokenExpired.mockReturnValue(false);
    await router.navigate(['/login']);
    expect(location.path()).toBe('/dashboard');
  });
});
