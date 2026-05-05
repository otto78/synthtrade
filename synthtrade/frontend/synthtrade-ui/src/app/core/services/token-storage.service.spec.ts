import { TokenStorageService } from './token-storage.service';

// JWT con exp nel futuro (anno 2099)
const VALID_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.' +
  btoa(JSON.stringify({ sub: 'user', exp: 4070908800 })) +
  '.signature';

// JWT con exp nel passato
const EXPIRED_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.' +
  btoa(JSON.stringify({ sub: 'user', exp: 1000000000 })) +
  '.signature';

describe('TokenStorageService', () => {
  let service: TokenStorageService;

  beforeEach(() => {
    localStorage.clear();
    service = new TokenStorageService();
  });

  it('should store and retrieve access token', () => {
    service.setTokens({ access_token: 'abc123', token_type: 'bearer' });
    expect(service.getAccessToken()).toBe('abc123');
  });

  it('should return null when no token stored', () => {
    expect(service.getAccessToken()).toBeNull();
  });

  it('should clear token', () => {
    service.setTokens({ access_token: 'abc123', token_type: 'bearer' });
    service.clear();
    expect(service.getAccessToken()).toBeNull();
  });

  it('should return false for isTokenExpired when token is valid', () => {
    service.setTokens({ access_token: VALID_TOKEN, token_type: 'bearer' });
    expect(service.isTokenExpired()).toBe(false);
  });

  it('should return true for isTokenExpired when token is expired', () => {
    service.setTokens({ access_token: EXPIRED_TOKEN, token_type: 'bearer' });
    expect(service.isTokenExpired()).toBe(true);
  });

  it('should return true for isTokenExpired when no token', () => {
    expect(service.isTokenExpired()).toBe(true);
  });

  it('should return true for isTokenExpired when token is malformed', () => {
    service.setTokens({ access_token: 'not.a.jwt', token_type: 'bearer' });
    expect(service.isTokenExpired()).toBe(true);
  });
});
