# Debug UI

This directory contains a dependency-free HTML/CSS/Vanilla JavaScript diagnostic page for the
documented `POST /resolve` API.

The page intentionally requests the same-origin `/resolve` route with `debug=true`. Serve these
files from the API origin (for example, mount `ui/` as the application's static root) so the UI
does not require an additional CORS policy. Static-file routing is an integration concern; the UI
does not change the FastAPI contract or implement resolution logic.

All API-supplied values are rendered through `textContent`. Candidate depth is clamped to the
contracted range of 1–25 before a request is sent.
