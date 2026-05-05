import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { SidebarComponent } from './sidebar.component';

describe('SidebarComponent', () => {
  let fixture: ComponentFixture<SidebarComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(SidebarComponent);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should render all nav items', () => {
    const items = el.querySelectorAll('.nav-item');
    expect(items.length).toBe(4); // Dashboard, Strategies, Active Trade, Logs
  });

  it('should render 4 anchor links in nav', () => {
    const links = el.querySelectorAll('a.nav-link');
    expect(links.length).toBe(4);
  });

  it('should toggle collapsed state on button click', () => {
    expect(fixture.componentInstance.collapsed()).toBe(false);
    (el.querySelector('.sidebar-toggle') as HTMLElement).click();
    fixture.detectChanges();
    expect(fixture.componentInstance.collapsed()).toBe(true);
  });

  it('should add sidebar--collapsed class when collapsed', () => {
    (el.querySelector('.sidebar-toggle') as HTMLElement).click();
    fixture.detectChanges();
    expect(el.querySelector('.sidebar')?.classList).toContain('sidebar--collapsed');
  });
});
