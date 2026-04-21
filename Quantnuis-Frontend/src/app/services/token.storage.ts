import { Injectable } from '@angular/core';

const TOKEN_KEY = 'quantnuis_token';
const TOKEN_EXP_KEY = 'quantnuis_token_exp';
const USER_KEY = 'quantnuis_user';

@Injectable({ providedIn: 'root' })
export class TokenStorage {

  encode(token: string): string {
    return btoa(encodeURIComponent(token).split('').reverse().join(''));
  }

  decode(encoded: string): string | null {
    try {
      return decodeURIComponent(atob(encoded).split('').reverse().join(''));
    } catch {
      return null;
    }
  }

  isExpired(): boolean {
    const expStr = localStorage.getItem(TOKEN_EXP_KEY);
    if (!expStr) return true;
    return Date.now() > parseInt(expStr, 10);
  }

  getToken(): string | null {
    if (this.isExpired()) {
      this.clear();
      return null;
    }
    const encoded = localStorage.getItem(TOKEN_KEY);
    if (!encoded) return null;
    return this.decode(encoded);
  }

  saveToken(token: string, expirationMinutes = 240): void {
    localStorage.setItem(TOKEN_KEY, this.encode(token));
    const expTime = Date.now() + expirationMinutes * 60 * 1000;
    localStorage.setItem(TOKEN_EXP_KEY, expTime.toString());
  }

  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXP_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem('access_token');
  }

  saveUser(user: any): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  getUser(): any | null {
    const cached = localStorage.getItem(USER_KEY);
    if (!cached) return null;
    try {
      return JSON.parse(cached);
    } catch {
      return null;
    }
  }
}
