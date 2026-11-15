# abla.co: handoff

Website for Abla IA, the Colombian restaurant AI (brand of the Colombian venture; separate from Conveasy).
Built 14-15 Nov 2026 from the Conveasy site generator, WhatsApp first. Domain abla.co (not connected yet).

## Build
- `python3 src/build.py` writes `docs/` (the site, for GitHub Pages) and `preview/` (same pages with a yellow preview bar).
- Texts: `src/content_es.py` is the master (Spanish, Colombia). `content_en.py`, `content_pt.py` (Brazil), `content_fr.py`
  have exactly the same structure; the build fails if a key or a list length differs from Spanish.
- Languages: es (root and x-default), pt, en, fr. 15 pages per language: home, WhatsApp IA, Teléfono IA, Tienda online y QR,
  Kiosco, Precios, 6 restaurant types (comidas rápidas, pizzerías, hamburgueserías, asaderos, sushi, todos), Nosotros,
  Contacto, Privacidad y términos.
- Prices live in `PRICE` in build.py (COP): WhatsApp IA 279.000/month + installation 349.000 once; reservations +34.900/month
  or reservations only 139.000/month; extra language 34.900/month each. In texts they are written as {wa}, {setup},
  {resv_addon}, {resv_only}, {lang} and formatted per language: $279.000 (es), COP 279.000 (pt), COP 279,000 (en),
  279 000 COP (fr). Phone AI, online store, kiosk and POS show "Cotización" (no price given yet).
- Facts used (all from the owner): WhatsApp AI main focus, 24/7, 50+ conversations at once (WhatsApp and voice), ticket printed
  in the kitchen, restaurants need a laptop and a ticket printer, Spanish included and 60+ languages as paid extras,
  sales team in Colombia that visits restaurants, POS also offered. Nothing else is claimed (no payment links, no dashboard
  features, no setup time, no trial, no clients or numbers).

## Still to fill (yellow markers, list in PLACEHOLDERS.txt)
- `WA_NUMBER` / `WA_DISPLAY` and `EMAIL` at the top of build.py. While empty, WhatsApp buttons go to the contact page and the
  contact form only shows a note; once WA_NUMBER is set the form opens WhatsApp with the request.
- Company: legal name, NIT, address, email, phone (footer, about, privacy page).
- Terms: contract term / cancellation / refunds, governing law; payment method and invoicing.
- Online store: own domain answer. Rotisserie FAQ: can orders be scheduled for later?

## Look
- Same base as conveasy.be (dark, star field) with a sunflower-yellow accent (#FFC83D) and the Abla mark: a yellow speech
  bubble with three typing dots (`LOGO_MARK` in build.py, `src/favicon.svg`, `src/apple-touch-icon.png`, `brand/`).
- Headings Plus Jakarta Sans, body Figtree.

## Animations (WhatsApp first)
- `wa_chat()`: a phone with a WhatsApp chat as the customer sees it (customer right in green, the AI left in white, reply
  buttons, typing dots and "escribiendo…"). Timelines in `TL` ("order": customer, AI, buttons, tap, customer, AI; "qa":
  customer, AI, customer, AI); `scenes_css()` writes the keyframes to assets/scenes.css. Without motion every message shows.
- Scenes: order (hero, with the kitchen ticket printing once the order is confirmed and a "52 chats" pill), menu question,
  reservation, tourist in another language (English on es/pt/fr, Portuguese on en), and `inbox()`: the 50+ chats list the
  AI works through while the counter goes 44 → 52.
- Every restaurant-type page has its own WhatsApp order chat (`chat` in S[...]) and its own ticket.
- Phone AI, online store and kiosk reuse the Conveasy scenes (pscene, wscene, kscene), in pesos and with ABLA tickets.

## Not done yet
- No GitHub repo / hosting yet: when the domain is ready, create a repo (same setup as conveasy-site: GitHub Pages from /docs),
  add docs/CNAME with abla.co, and set the DNS at the registrar (A records to GitHub Pages, CNAME www).
- No live demos (the Conveasy voice demo and chat demo are Conveasy's; their keys are not in this site).
