export interface User {
  id: string;
  email: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: 'bearer';
}

export interface JwtPayload {
  sub: string;
  exp: number;
  iat?: number;
}
