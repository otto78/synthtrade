/**
 * Opportunity API Service
 * REST client for opportunity data
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Opportunity } from '../models/opportunity.model';

@Injectable({
  providedIn: 'root',
})
export class OpportunityApiService {
  private readonly API_URL = '/api/scalping/opportunities';

  constructor(private http: HttpClient) {}

  /** Get opportunities list with filters */
  getOpportunities(filters?: {
    urgency?: string;
    category?: string;
    limit?: number;
  }): Observable<Opportunity[]> {
    const params: any = { limit: filters?.limit || 50 };
    if (filters?.urgency) params.urgency = filters.urgency;
    if (filters?.category) params.category = filters.category;

    return this.http.get<Opportunity[]>(this.API_URL, { params });
  }

  /** Mark opportunity as watched */
  watchOpportunity(id: string): Observable<any> {
    return this.http.post(`${this.API_URL}/${id}/watchlist`, {});
  }

  /** Mark opportunity as ignored */
  ignoreOpportunity(id: string): Observable<any> {
    return this.http.post(`${this.API_URL}/${id}/ignore`, {});
  }
}