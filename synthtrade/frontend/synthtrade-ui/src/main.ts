import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

const params = new URLSearchParams(window.location.search);
const route = params.get('route');
if (route) {
  // GitHub Pages serves 404.html on deep links; it redirects here with ?route=...
  // Restore the original route before Angular boots so refresh works on every page.
  // The base href (e.g. /synthtrade/) MUST be kept: replaceState with a leading
  // slash would point outside the deployed app (e.g. /strategies) and the next
  // refresh would hit GitHub's default 404 instead of this page.
  const base = document.querySelector('base')?.getAttribute('href') ?? '/';
  history.replaceState(null, '', base + route.replace(/^\//, ''));
}

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
