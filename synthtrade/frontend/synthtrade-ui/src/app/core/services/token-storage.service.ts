import { Injectable } from '@angular/core';
import { AuthTokens, JwtPayload } from '../models/user.model';

const TOKEN_KEY = 'st_access_token';

@Injectable({ providedIn: 'root' })
export class TokenStorageService {
  setTokens(tokens: AuthTokens): void {
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
  }

  getAccessToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  isTokenExpired(): boolean {
    const token = this.getAccessToken();
    if (!token) return true;
    try {
      const payload: JwtPayload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }
}
