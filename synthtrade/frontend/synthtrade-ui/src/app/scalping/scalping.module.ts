/**
 * Scalping Module
 * Angular module for Scalping Dashboard v2.0
 */

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';

import { ScalpingRoutingModule } from './scalping-routing.module';
import { ScalpingWsService } from './services/scalping-ws.service';
import { IntelligenceApiService } from './services/intelligence-api.service';
import { OpportunityApiService } from './services/opportunity-api.service';
import { BacktestApiService } from './services/backtest-api.service';

@NgModule({
  declarations: [],
  imports: [CommonModule, HttpClientModule, ScalpingRoutingModule],
  providers: [ScalpingWsService, IntelligenceApiService, OpportunityApiService, BacktestApiService],
})
export class ScalpingModule {}