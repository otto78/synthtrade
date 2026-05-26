/**
 * Position API Service
 * REST client for position data
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Position } from '../models/position.model';

@Injectable({
  providedIn: 'root',
})
export class PositionApiService {
  private readonly API_URL = '/api/scalping/position';

  constructor(private http: HttpClient) {}

  /** Get current open position */
  getCurrent(): Observable<Position | null> {
    return this.http.get<Position | null>(this.API_URL);
  }

  /** List all positions */
  getList(): Observable<Position[]> {
    return this.http.get<Position[]>(`${this.API_URL}/list`);
  }
}