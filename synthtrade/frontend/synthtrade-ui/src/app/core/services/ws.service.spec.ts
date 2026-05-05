import { WsService } from './ws.service';
import { TokenStorageService } from './token-storage.service';
import { WsMessageType } from '../models/ws-message.model';

// Mock WebSocket
class MockWebSocket {
  static instance: MockWebSocket;
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  readyState = WebSocket.OPEN;
  close = jest.fn();
  send = jest.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instance = this;
  }
}

describe('WsService', () => {
  let service: WsService;
  let tokenStorage: jest.Mocked<TokenStorageService>;

  beforeEach(() => {
    tokenStorage = { getAccessToken: jest.fn().mockReturnValue('test-token') } as any;
    (global as any).WebSocket = MockWebSocket;
    service = new WsService(tokenStorage);
  });

  afterEach(() => {
    service.disconnect();
    jest.clearAllTimers();
  });

  it('should open WebSocket with token as query param', () => {
    service.connect().subscribe();
    expect(MockWebSocket.instance.url).toContain('token=test-token');
  });

  it('should emit parsed messages on messages$', (done) => {
    const msg = { type: WsMessageType.Ping };

    service.connect().subscribe(m => {
      expect(m).toEqual(msg);
      done();
    });

    MockWebSocket.instance.onmessage!({ data: JSON.stringify(msg) } as MessageEvent);
  });

  it('should complete observable on disconnect', (done) => {
    service.connect().subscribe({ complete: () => done() });
    service.disconnect();
  });

  it('should call ws.close on disconnect', () => {
    service.connect().subscribe();
    service.disconnect();
    expect(MockWebSocket.instance.close).toHaveBeenCalled();
  });

  it('on<T> should filter messages by type', (done) => {
    const priceMsg = { type: WsMessageType.Price, payload: { pair: 'BTC/USDT', price: 62000 } };
    const pingMsg = { type: WsMessageType.Ping };

    service.connect().subscribe();

    service.on(WsMessageType.Price).subscribe(m => {
      expect(m.type).toBe(WsMessageType.Price);
      done();
    });

    MockWebSocket.instance.onmessage!({ data: JSON.stringify(pingMsg) } as MessageEvent);
    MockWebSocket.instance.onmessage!({ data: JSON.stringify(priceMsg) } as MessageEvent);
  });
});
