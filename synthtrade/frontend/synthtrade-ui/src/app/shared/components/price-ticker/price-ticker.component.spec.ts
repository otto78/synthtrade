import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PriceTickerComponent } from './price-ticker.component';

describe('PriceTickerComponent', () => {
  let fixture: ComponentFixture<PriceTickerComponent>;

  function create(price: number, decimals = 2) {
    fixture = TestBed.createComponent(PriceTickerComponent);
    fixture.componentRef.setInput('price', price);
    fixture.componentRef.setInput('decimals', decimals);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [PriceTickerComponent] }));

  it('should render price with correct decimals', () => {
    const el = create(62000.5, 2);
    expect(el.querySelector('.price')?.textContent?.trim()).toBe('62,000.50');
  });

  it('should apply flash-up class when price increases', () => {
    fixture = TestBed.createComponent(PriceTickerComponent);
    fixture.componentRef.setInput('price', 100);
    fixture.detectChanges();
    fixture.componentRef.setInput('price', 110);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.price')?.classList).toContain('flash-up');
  });

  it('should apply flash-down class when price decreases', () => {
    fixture = TestBed.createComponent(PriceTickerComponent);
    fixture.componentRef.setInput('price', 100);
    fixture.detectChanges();
    fixture.componentRef.setInput('price', 90);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.price')?.classList).toContain('flash-down');
  });

  it('should remove flash class on animationend', () => {
    fixture = TestBed.createComponent(PriceTickerComponent);
    fixture.componentRef.setInput('price', 100);
    fixture.detectChanges();
    fixture.componentRef.setInput('price', 110);
    fixture.detectChanges();
    const priceEl = fixture.nativeElement.querySelector('.price') as HTMLElement;
    priceEl.dispatchEvent(new Event('animationend'));
    fixture.detectChanges();
    expect(priceEl.classList).not.toContain('flash-up');
  });
});
