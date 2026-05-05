import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, tap } from 'rxjs';
import { TokenStorageService } from './token-storage.service';
import { AuthTokens } from '../models/user.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private tokenStorage = inject(TokenStorageService);

  currentUser$ = new BehaviorSubject<string | null>(null);

  login(password: string) {
    return this.http.post<AuthTokens>(`${environment.apiUrl}/auth/login`, { password }).pipe(
      tap((tokens) => {
        this.tokenStorage.setTokens(tokens);
        this.currentUser$.next('user');
      })
    );
  }

  logout(): void {
    this.tokenStorage.clear();
    this.currentUser$.next(null);
    this.router.navigate(['/login']);
  }

  isAuthenticated(): boolean {
    return !!this.tokenStorage.getAccessToken() && !this.tokenStorage.isTokenExpired();
  }
}
