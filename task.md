# Scrabble Word Builder — Task Board

Actionable, trackable breakdown of [plan.md](plan.md). Tasks are grouped by phase and
ordered by priority. Legend: 🔴 critical · 🟠 high · 🟡 medium · 🟢 nice-to-have.

**Suggested order:** finish Phase 0–2 (correctness, safety, honesty) before Phase 4+.

---

## Phase 0 — Truth & Hygiene 🔴

- [x] **T0.1** 🔴 Fix "Flask → FastAPI" everywhere it's wrong.
  - Files: [README.md](README.md), [docker-compose.yml](docker-compose.yml)
    (`FLASK_ENV`/`FLASK_APP`/`FLASK_RUN_*` → uvicorn/`PORT` equivalents),
    [package.json](package.json) (description), [start-services.bat](start-services.bat)
    ("Starting Flask backend" text).
  - ✅ Done when: no stray "Flask" references; compose env vars are meaningful to uvicorn.

- [x] **T0.2** 🔴 Resolve duplicate Next config.
  - Keep one file. Merge `output: 'standalone'` + `rewrites()` from
    [frontend/next.config.js](frontend/next.config.js) and delete/junk
    [frontend/next.config.mjs](frontend/next.config.mjs).
  - ✅ Done when: `docker build -f Dockerfile.frontend` produces a working standalone build.

- [x] **T0.3** 🔴 Make the frontend API URL environment-driven.
  - Replace the hardcoded `http://localhost:5000` in
    [frontend/app/page.tsx](frontend/app/page.tsx) with a helper reading
    `NEXT_PUBLIC_API_URL` (or use the Next `rewrites` proxy via a relative `/api/...`).
  - ✅ Done when: the same build works locally and in Docker with no code change.

- [x] **T0.4** 🟠 Set real site metadata.
  - [frontend/app/layout.tsx](frontend/app/layout.tsx): replace "v0 App" title/description
    with proper title, description, and Open Graph tags.

- [x] **T0.5** 🟡 Remove dead code & doc clutter.
  - Delete non-functional [ui.py](ui.py) (or convert to a note in README).
  - Consolidate `DOCKER_COMPLETE.md`, `DOCKER_SETUP.md`, `INTEGRATION_COMPLETE.md`
    into a single docs section; remove the "process log" style files.

---

## Phase 1 — Core Engine & Correctness 🔴

- [x] **T1.1** 🔴 Extract a shared `scrabble_engine` package.
  - New module (e.g. `scrabble_engine/__init__.py`) holding `scores`, `word_score`,
    and the word-finding logic. Import it from [app.py](app.py) and [scrabble.py](scrabble.py).
  - ✅ Done when: zero duplicated logic between API and CLI.

- [x] **T1.2** 🔴 Replace permutations with an **anagram-signature index**.
  - Precompute `signature -> [words]` where `signature = "".join(sorted(word))`.
  - Query by iterating rack **combinations** (with blank expansion) and looking up
    signatures — not permutations.
  - ✅ Done when: hard 7–8 letter racks return in < 100 ms; results match the old
    engine on the golden test set (T1.5).

- [x] **T1.3** 🔴 Fix multi-blank support.
  - Bug today: all blanks collapse to the same replacement letter in
    [app.py](app.py)/[scrabble.py](scrabble.py). Support up to 2 blanks as
    **independent** wildcards.
  - ✅ Done when: rack `"C T ?"` and `"? ?"` produce correct, distinct fills.

- [x] **T1.4** 🟠 Fix blank-aware scoring & the mutable default arg.
  - Score blanks as 0 regardless of where board letters are inserted (indices must
    track the final word). Change `word_score(word, zero_indices=[])` to use `None`.
  - ✅ Done when: a word played with a blank scores that tile as 0 in all positions.

- [x] **T1.5** 🔴 Golden tests lock behavior **before/after** refactor.
  - `pytest` cases for: known racks → expected word sets & scores; blanks; board letters;
    empty/edge inputs.
  - ✅ Done when: tests pass on both old and new engine (proves equivalence + fixes).

---

## Phase 2 — Security & Robustness 🟠

- [ ] **T2.1** 🔴 Fix CORS.
  - In [app.py](app.py), drop `allow_origins=["*"]` + `allow_credentials=True` combo.
    Use an explicit allowlist from env (`ALLOWED_ORIGINS`), credentials off unless needed.

- [ ] **T2.2** 🔴 Bound inputs to prevent DoS.
  - Reject racks longer than a configurable max (e.g. 10 letters, ≤ 2 blanks) with HTTP
    422 and a clear message, in the `/api/find-words` handler.

- [ ] **T2.3** 🟠 Add lightweight rate limiting (e.g. `slowapi`) to the API.

- [ ] **T2.4** 🟠 Real frontend error & empty states.
  - Surface API/network errors to the user (toast/alert) instead of only `console.error`
    in [frontend/app/page.tsx](frontend/app/page.tsx); show a friendly "no words found".
  - Make [frontend/app/loading.tsx](frontend/app/loading.tsx) render an actual skeleton.

---

## Phase 3 — Testing & CI 🟠

- [ ] **T3.1** 🟠 Backend tests: engine + API (`pytest`, `httpx`/`TestClient`).
- [ ] **T3.2** 🟡 Frontend smoke test (`vitest`/RTL or a Playwright happy-path).
- [ ] **T3.3** 🟠 GitHub Actions CI: lint + type-check + tests + `docker build` on PR.
- [ ] **T3.4** 🟡 Add `.env.example` and a "Configuration" section documenting every var.

---

## Phase 4 — Creative Features 🟢

- [ ] **T4.1** 🟠 **Pattern / wildcard search** — new `/api/pattern` supporting `C_T`,
  `*ING`, `.A.E`. Great for crosswords + Scrabble hooks. Add a tab/toggle in the UI.
- [ ] **T4.2** 🟡 **Word validator** — `/api/validate?word=...` + a small "Is it a word?"
  widget; show definition when available.
- [ ] **T4.3** 🟡 **Definitions** — enrich results (bundled compact source or cached
  free dictionary API) shown on hover/expand of a word.
- [ ] **T4.4** 🟠 **Premium-square-aware scoring** — make the interactive board in
  [frontend/components/scrabble-board.tsx](frontend/components/scrabble-board.tsx)
  compute *actual* play value using letter/word multipliers (currently decorative).
- [ ] **T4.5** 🟢 **Random rack generator** (real Scrabble tile distribution) +
  **word of the day**.
- [ ] **T4.6** 🟡 **Filters & sorting** — by length, score, alphabetical, "must contain".
- [ ] **T4.7** 🟢 **Favorites & history** (localStorage) + copy-to-clipboard & share.

---

## Phase 5 — Polish & Delight 🟢

- [ ] **T5.1** 🟡 Wire up dark mode via the existing
  [frontend/components/theme-provider.tsx](frontend/components/theme-provider.tsx)
  in [frontend/app/layout.tsx](frontend/app/layout.tsx); add a theme toggle.
- [ ] **T5.2** 🟢 Accessibility pass — keyboard nav for the board, focus rings, ARIA labels.
- [ ] **T5.3** 🟢 Virtualize long result lists for performance.
- [ ] **T5.4** 🟢 Richer `/api/health` (version, word count, uptime) + structured logging.
- [ ] **T5.5** 🟢 Optional PWA / offline mode with a bundled compact dictionary.

---

## Quick-Win Starter Set

If picking a first batch, do these together for maximum visible impact with low risk:
**T0.1**, **T0.2**, **T0.3**, **T1.5** (write golden tests), then **T1.2** (the engine
rewrite) guarded by those tests.

---

## Progress Tracking

| Phase | Focus | Priority | Status |
|-------|-------|----------|--------|
| 0 | Truth & Hygiene | 🔴 | ✅ Done |
| 1 | Core Engine & Correctness | 🔴 | ✅ Done |
| 2 | Security & Robustness | 🟠 | ☐ Not started |
| 3 | Testing & CI | 🟠 | ☐ Not started |
| 4 | Creative Features | 🟢 | ☐ Not started |
| 5 | Polish & Delight | 🟢 | ☐ Not started |
