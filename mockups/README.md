# Forte UI mockup

Open `mockups/index.html` in a browser. Demo scenarios switch in the header. Player uses `video/sample.webm` (format sample, not dataset). JSON panel follows the jury contract plus optional fields agreed with backend (rule_ref, confidence, window_sec, tracks, unanalyzed_ranges, needs_manual_review).

## v8 (React app, Forte design system)

- `forte_ui_v8.html` — single self-contained file (frames, poster and webm inlined as data URIs); opens via `file://`, no server needed. Same build as `frontend-app/dist`.
- Screens: upload → job progress (queued → processing stages → done/failed, simulated `JobClient`, ready for `HttpJobClient`) → results (verdict banner, timeline, findings, violation card with evidence frames + lightbox, adilet sources with verified badge); secondary details (procedure baseline, API JSON, taxonomy) behind tabs.
- `forte_design.md` — Forte brand-book extract used for tokens (colours, gradients, Open Sans, radii, components).
- Screenshots: `screens/fa8_*.png`.
