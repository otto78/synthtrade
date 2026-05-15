import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ActiveTradeRowComponent } from './active-trade-row.component';
import { Subject } from 'rxjs';
import { WsService } from '../../../core/services/ws.service';
import { WsMessageType } from '../../../core/models/ws-message.model';

describe('ActiveTradeRowComponent', () => {
  let fixture: ComponentFixture<ActiveTradeRowComponent>;
  let el: HTMLElement;
  let wsService: jest.Mocked<WsService>;
  let wsSubject: Subject<any>;

  const mockTrade = {
    id: 't1',
    strategy_id: 's1',
    strategy_title: 'EMA Cross',
    symbol: 'BTC/USDT',
    side: 'BUY' as const,
    entry_price: 50000,
    current_price: 52000,
    unrealized_pnl_pct: 4.0,
    quantity: 0.015,
    opened_at: '2026-05-14T10:00:00Z',
  };

  beforeEach(async () => {
    wsSubject = new Subject();
    wsService = {
      on: jest.fn().mockReturnValue(wsSubject.asObservable()),
    } as any;

    await TestBed.configureTestingModule({
      imports: [ActiveTradeRowComponent],
      providers: [
        { provide: WsService, useValue: wsService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ActiveTradeRowComponent);
    fixture.componentRef.setInput('tradeData', mockTrade);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  // Test 1: Render trade info correctly
  it('should render trade symbol and direction', () => {
    expect(el.querySelector('.ar-symbol')?.textContent).toContain('BTC/USDT');
    expect(el.querySelector('.ar-side')?.textContent).toContain('BUY');
    expect(el.querySelector('.ar-side')?.classList).toContain('buy');
  });

  // Test 2: SELL side gets sell class
  it('should apply sell class when side is SELL', () => {
    fixture.componentRef.setInput('tradeData', { ...mockTrade, side: 'SELL' });
    fixture.detectChanges();
    expect(el.querySelector('.ar-side')?.classList).toContain('sell');
  });

  // Test 3: Show entry price and quantity
  it('should display entry price and quantity', () => {
    expect(el.querySelector('.ar-entry')?.textContent).toContain('50,000');
    expect(el.querySelector('.ar-qty')?.textContent).toContain('0.015');
  });

  // Test 4: P&L positive class
  it('should apply positive class when pnl > 0', () => {
    // With current_price=52000 and entry_price=50000, pnl = (52000-50000)/50000*100 = 4%
    const pnlEl = el.querySelector('.ar-pnl');
    expect(pnlEl?.classList).toContain('positive');
    expect(pnlEl?.textContent).toContain('4');
  });

  // Test 5: P&L negative class
  it('should apply negative class when current_price < entry_price', () => {
    fixture.componentRef.setInput('tradeData', { ...mockTrade, entry_price: 50000, current_price: 48000 });
    fixture.detectChanges();
    const pnlEl = el.querySelector('.ar-pnl');
    expect(pnlEl?.classList).toContain('negative');
    expect(pnlEl?.textContent).toContain('-4');
  });

  // Test 6: Flash animation class on P&L change via WS price update
  it('should add flash-up class when WS price update increases P&L', fakeAsync(() => {
    wsSubject.next({
      type: WsMessageType.Price,
      payload: { pair: 'BTC/USDT', price: 53000 }
    });
    fixture.detectChanges();

    const pnlEl = el.querySelector('.ar-pnl');
    expect(pnlEl?.classList).toContain('flash-up');

    tick(600);
    fixture.detectChanges();
    expect(pnlEl?.classList).not.toContain('flash-up');
  }));

  // Test 7: Flash-down animation class when price drops
  it('should add flash-down class when WS price update decreases P&L', fakeAsync(() => {
    wsSubject.next({
      type: WsMessageType.Price,
      payload: { pair: 'BTC/USDT', price: 48000 }
    });
    fixture.detectChanges();

    const pnlEl = el.querySelector('.ar-pnl');
    expect(pnlEl?.classList).toContain('flash-down');

    tick(600);
    fixture.detectChanges();
    expect(pnlEl?.classList).not.toContain('flash-down');
  }));

  // Test 8: Only react to WS price for the correct symbol
  it('should not react to WS price updates for different symbols', () => {
    const currentPrice = fixture.componentInstance.currentPrice();

    wsSubject.next({
      type: WsMessageType.Price,
      payload: { pair: 'ETH/USDT', price: 3000 }
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.currentPrice()).toBe(currentPrice);
  });

  // Test 9: Calculate position value in EUR
  it('should calculate position value in EUR', () => {
    // position_value_eur = entry_price * quantity = 50000 * 0.015 = 750
    const valueEl = el.querySelector('.ar-value');
    expect(valueEl?.textContent).toContain('750');
  });

  // Test 10: Opened date formatted
  it('should display opened date', () => {
    const dateEl = el.querySelector('.ar-date');
    expect(dateEl).toBeTruthy();
    expect(dateEl?.textContent).toContain('14/05');
  });

  // Test 11: WS subscription cleanup on destroy
  it('should unsubscribe from WS on destroy', () => {
    fixture.destroy();
    expect(fixture.componentInstance['wsSub']?.closed).toBeTruthy();
  });
});