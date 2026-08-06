import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

const params = new URLSearchParams(window.location.search);
const route = params.get('route');
if (route) {
  // GitHub Pages serves 404.html on deep links; it redirects here with ?route=...
  // Restore the original route before Angular boots so refresh works on every page.
  history.replaceState(null, '', route);
}

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
