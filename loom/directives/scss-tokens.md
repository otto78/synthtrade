# Direttiva: SCSS Design Tokens — SynthTrade

## Obiettivo
Fonte di verità per tutti i design token del frontend SynthTrade. Usare SEMPRE queste variabili, mai valori hardcoded.

---

## File di riferimento
`synthtrade/frontend/src/styles/_variables.scss`

---

## Background

```scss
--bg-base:        #07090C;   // Sfondo principale (quasi nero)
--bg-surface:     #0D1117;   // Card, sidebar
--bg-elevated:    #161B22;   // Dropdown, modal, tooltip
--bg-overlay:     #1C2128;   // Hover states, selected rows
```

---

## Brand Colors

```scss
--accent-primary:   #F0B90B;              // Gold — CTA, segnali attivi, border focus
--accent-glow:      rgba(240,185,11,0.15); // Glow diffuso per animazioni
--accent-secondary: #00D4AA;              // Teal — AI score, conferme
```

---

## Semantic Colors

```scss
--color-buy:    #0ECB81;   // Verde — long, profit, ACTIVE
--color-sell:   #F6465D;   // Rosso — short, loss, REJECT
--color-warn:   #F0B90B;   // Giallo — PENDING, warning
--color-info:   #1890FF;   // Blu — info, neutro
```

---

## Testo

```scss
--text-primary:   #EAECEF;
--text-secondary: #848E9C;
--text-muted:     #474D57;
```

---

## Bordi

```scss
--border-default: rgba(234,236,239,0.06);
--border-focus:   rgba(240,185,11,0.4);
--border-active:  var(--accent-primary);
```

---

## Tipografia

```scss
$font-display: 'Chakra Petch', sans-serif;  // Logo, H1–H3, ticker labels
$font-body:    'DM Sans', sans-serif;       // Testo UI, bottoni, label
$font-mono:    'JetBrains Mono', monospace; // Prezzi, hash, timestamp, score
```

Google Fonts da importare in `global.scss`:
```scss
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
```

---

## Spacing (base 8px)

```scss
$space-1: 4px;
$space-2: 8px;
$space-3: 12px;
$space-4: 16px;
$space-6: 24px;
$space-8: 32px;
$space-12: 48px;
$space-16: 64px;
```

---

## Border Radius

```scss
$radius-sm: 4px;   // Bottoni, badge, input
$radius-md: 8px;   // Card, pannelli
$radius-lg: 12px;  // Modal, drawer
```

---

## Layout

```scss
$sidebar-width: 240px;
$topbar-height: 56px;
```

---

## Animazioni

```scss
// Strategia attiva — glow pulsante
@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 0 1px var(--accent-primary), 0 0 12px var(--accent-glow); }
  50%       { box-shadow: 0 0 0 1px var(--accent-primary), 0 0 28px var(--accent-glow); }
}

// Prezzo aggiornato — flash colore
@keyframes price-up   { 0%,100%{color:var(--text-primary)} 40%{color:var(--color-buy)} }
@keyframes price-down { 0%,100%{color:var(--text-primary)} 40%{color:var(--color-sell)} }

// Sidebar nav hover
.nav-item:hover {
  background: linear-gradient(90deg, var(--accent-glow), transparent);
  border-left: 2px solid var(--accent-primary);
  transition: all 0.2s ease;
}

// Scanline overlay — effetto terminale
.terminal-surface::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg, transparent 0px, transparent 2px,
    rgba(255,255,255,0.012) 2px, rgba(255,255,255,0.012) 4px
  );
  pointer-events: none;
  border-radius: inherit;
}
```

---

## Status → Colore (mapping)

| Status | Colore | Variabile |
|--------|--------|-----------|
| PENDING | Giallo | `--color-warn` |
| ACTIVE | Verde | `--color-buy` |
| APPROVED | Verde | `--color-buy` |
| REJECTED | Rosso | `--color-sell` |
| EXPIRED | Grigio | `--text-muted` |
| BUY | Verde | `--color-buy` |
| SELL | Rosso | `--color-sell` |
| BLOCK | Giallo | `--color-warn` |
| ERROR | Rosso | `--color-sell` |

---

**Versione:** 1.0.0
**Ultima modifica:** 2025-01-16
