import { Injectable } from '@angular/core';
import { Observable, of, BehaviorSubject } from 'rxjs';
import { delay, tap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.getStoredAuthState());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor() {}

  login(username: string, password: string): Observable<boolean> {
    // Simple demo authentication - in production, this would call a real API
    const isValid = username === 'admin' && password === 'admin';
    
    return of(isValid).pipe(
      delay(1000), // Simulate API call delay
      tap(success => {
        if (success) {
          localStorage.setItem('isAuthenticated', 'true');
          localStorage.setItem('username', username);
          this.isAuthenticatedSubject.next(true);
        }
      })
    );
  }

  logout(): void {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('username');
    this.isAuthenticatedSubject.next(false);
  }

  isAuthenticated(): boolean {
    return this.isAuthenticatedSubject.value;
  }

  getUsername(): string | null {
    return localStorage.getItem('username');
  }

  private getStoredAuthState(): boolean {
    return localStorage.getItem('isAuthenticated') === 'true';
  }
}