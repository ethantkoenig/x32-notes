# X32 Scene Notes — Implementation Plan

A local web app that runs alongside X32-Edit on macOS, reads X32 scene/preset files from
disk, and lets you attach and review notes for live recall during services. Accessible from
a phone or tablet at the soundboard over the local network.

---

## Goals & Non-Goals

**Goals**
- Parse and display X32 scene, snippet, and channel preset files
- Attach, edit, and view plain-text notes on any scene/preset
- Visualize key channel parameters (EQ curves, compressor, gate) in a readable way
- Accessible from phone/tablet over LAN


**Non-Goals (for now)**
- Sending OSC commands to the board
- Live sync with X32-Edit or the board
- Multi-user access or authentication
- Cloud sync or backup

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Server | Python 3.11+ / FastAPI + Uvicorn | Async-friendly, easy to extend, familiar |
| File watching | `watchdog` | Detect when X32-Edit saves a scene |
| Frontend | Vanilla JS + Alpine.js | Low overhead for a personal tool |
| EQ visualization | Canvas API or Chart.js | Browser-native, no build step required |
| Notes storage | SQLite via `aiosqlite` | Simple, portable, queryable |

---

## Repository Layout

```
x32-notes/
├── server/
│   ├── main.py               # FastAPI app + Uvicorn entry point
│   ├── config.py             # Paths, settings (loaded from config.toml)
│   ├── watcher.py            # watchdog observer for X32-Edit scene directory
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── scene.py          # Parse .scn files
│   │   ├── snippet.py        # Parse .snp files
│   │   ├── channel.py        # Parse .chn preset files
│   │   └── parameters.py     # Shared parameter mapping (EQ bands, compressor, etc.)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py       # aiosqlite setup, migrations
│   │   └── notes.py          # CRUD for notes
│   └── routers/
│       ├── scenes.py         # GET /scenes, GET /scenes/{id}
│       ├── notes.py          # GET/POST/PUT/DELETE /notes
│       └── health.py         # GET /health
├── frontend/
│   ├── index.html            # Scene list view
│   ├── scene.html            # Scene detail view
│   ├── components/
│   │   ├── eq-curve.js       # EQ visualization (Canvas)
│   │   ├── compressor.js     # Compressor display
│   │   └── channel-strip.js  # Single channel summary card
│   ├── css/
│   │   └── app.css
│   └── js/
│       ├── app.js            # Alpine.js root
│       ├── api.js            # fetch() wrappers for all API endpoints
│       └── utils.js          # dB conversion, frequency formatting, etc.
├── config.toml               # User-editable: scene dir path, port, etc.
├── requirements.txt
├── README.md
└── PLAN.md
```

---

## Phase 1 — File Parsing

**Goal:** Reliably read X32-Edit's file formats and extract the parameters needed for
display and notes.

### X32 File Format Primer

X32-Edit saves files as plain text with a structured parameter format. Each line is
an OSC-style address/value pair, e.g.:

```
/ch/01/eq/1/type 5
/ch/01/eq/1/f 1000.0
/ch/01/eq/1/g 3.0
/ch/01/eq/1/q 2.0
/ch/01/mix/fader 0.75
/ch/01/config/name "Kick"
```

**File types:**
- `.scn` — full console snapshot (all channels, buses, effects, routing)
- `.snp` — snippet (partial snapshot; only specific parameter groups)
- `.chn` — single channel preset (EQ, dynamics, config for one channel)

### Tasks

- [ ] Write `parser/parameters.py` — define the parameter paths to extract per channel:
  - Config: name, color, icon
  - EQ: 4 bands × (type, frequency, gain, Q)
  - Compressor: threshold, ratio, attack, release, knee, gain
  - Gate: threshold, range, attack, hold, release
  - Fader level and mute state
- [ ] Write `parser/scene.py` — parse `.scn` files into a structured dict keyed by
  channel index
- [ ] Write `parser/channel.py` — parse `.chn` files (subset of scene parser)
- [ ] Write `parser/snippet.py` — parse `.snp` files; handle the fact that not all
  parameters may be present
- [ ] Write unit tests for each parser against sample files captured from a real X32
  Compact

### Notes on Robustness

- Be defensive: parameters may be missing (especially in snippets). Use `.get()` with
  sensible defaults everywhere.
- Log unrecognized parameter paths rather than raising — future firmware updates may
  add new paths.
- Store the raw parsed dict alongside the structured representation so nothing is
  discarded.

---

## Phase 2 — Backend API

**Goal:** FastAPI server that exposes scenes/presets and their notes, watches the
filesystem for changes, and serves the frontend.

### Data Model

**SQLite schema:**

```sql
CREATE TABLE notes (
    file_path   TEXT PRIMARY KEY,   -- Relative path from scene_dir, e.g. "Scenes/SundayMorning.scn"
    file_name   TEXT NOT NULL,      -- e.g. "SundayMorning.scn" (derived; stored for fast display)
    note        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,      -- ISO 8601
    updated_at  TEXT NOT NULL
);
```

Keying on `file_path` is simple and sufficient. The known limitation is that if a
file is renamed in X32-Edit, the note becomes orphaned. In practice this is unlikely
to be a frequent problem — scene names tend to be stable once set.

### API Endpoints

```
GET  /api/scenes
     Returns list of all scene/preset files found in the watched directory,
     each with: file_name, file_path, has_note, last_modified

GET  /api/scenes/{file_path:path}
     Returns parsed parameters for a specific scene + its note (if any)

GET  /api/notes/{file_path:path}
     Returns the note for a scene (404 if none)

POST /api/notes/{file_path:path}
     Create or update note. Body: { "note": "string" }

DELETE /api/notes/{file_path:path}
     Remove a note

GET  /health
     Returns { "status": "ok", "scene_count": N }
```

### File Watcher

Use `watchdog` to monitor the X32-Edit scene directory. On any file create/modify
event for `.scn`, `.snp`, or `.chn` files:
1. Re-parse the file
2. Emit a server-sent event (SSE) so the frontend can refresh without polling

On a delete event, the note row is left in SQLite — don't silently discard notes
just because a file disappears temporarily (e.g. X32-Edit rewriting it).

### Tasks

- [ ] Set up FastAPI app with static file serving for `frontend/`
- [ ] Implement `db/database.py` with schema creation and simple migration support
- [ ] Implement `db/notes.py` CRUD functions
- [ ] Implement `routers/scenes.py` — scans directory, parses files, joins with notes
- [ ] Implement `routers/notes.py` — note CRUD endpoints
- [ ] Implement `watcher.py` — watchdog observer + SSE event emitter
- [ ] Add `GET /api/events` SSE endpoint for live file-change notifications
- [ ] Add `config.toml` loading via `tomllib` (stdlib in Python 3.11+):
  ```toml
  [server]
  host = "0.0.0.0"
  port = 8765

  [x32]
  scene_dir = "/Users/yourname/Documents/X32Edit/Scenes"
  ```
- [ ] Write integration tests for all endpoints using FastAPI's `TestClient`

---

## Phase 3 — Frontend

**Goal:** A clean, phone-friendly web UI for browsing scenes and reading/writing notes.

### Views

**Scene List (`index.html`)**
- Search/filter by file name or note content
- Sort by: file name, last modified, has note
- Each row: file name, file type badge (Scene / Snippet / Channel), note preview
  (first line), last modified date
- Tap a row → Scene Detail

**Scene Detail (`scene.html`)**
- Header: file name, file type, last modified
- Note editor: plain textarea, auto-saves on blur (no save button needed)
- Channel strips: one card per channel present in the scene
  - Channel name + color indicator
  - EQ curve visualization
  - Compressor settings summary (threshold, ratio, GR meter static display)
  - Gate settings summary
  - Fader level (dB)
  - Mute state

### EQ Curve Visualization

Draw on a `<canvas>` element. Parameters needed per band:
- Type (shelf, peak, highpass, lowpass, notch)
- Frequency (Hz)
- Gain (dB, ±15)
- Q

Render a frequency response curve from 20Hz–20kHz on a log scale. Keep it small
enough to be readable at phone size — aim for ~300×120px per channel.

Use established filter math for biquad frequency response:
- Peaking EQ: standard RBJ cookbook formula
- Shelves: low/high shelf formulas
- HPF/LPF: Butterworth response approximation

### Alpine.js Usage

Keep Alpine lightweight — use it for:
- Search/filter state on the list view
- Note dirty-state tracking (unsaved changes indicator)
- SSE event handling to refresh the list when files change

Avoid pulling in a full component framework. The app has two views and modest
interactivity.

### Tasks

- [ ] Build scene list view with search and sort
- [ ] Build scene detail view layout (mobile-first)
- [ ] Implement `eq-curve.js` Canvas renderer
- [ ] Implement `compressor.js` static display component
- [ ] Implement `channel-strip.js` combining the above
- [ ] Implement `api.js` fetch wrappers with error handling
- [ ] Wire up SSE in `app.js` for live list refresh
- [ ] Implement auto-save note on blur with a "saved" confirmation flash
- [ ] Test layout on iPhone and iPad screen sizes

---

## Phase 4 — Polish & Reliability

**Goal:** Make the tool dependable enough to trust on a Sunday morning.

### Note Orphan Handling

If a scene file is renamed in X32-Edit, its note becomes orphaned — the note row
remains in SQLite keyed to the old path, but no file matches it anymore. This is an
accepted limitation given how rarely scene names change in practice.

To surface orphaned notes rather than silently losing them:
- The scene list endpoint joins files on disk with notes in SQLite; unmatched note
  rows are returned as an "orphaned notes" list
- The UI shows a simple "Orphaned Notes" section at the bottom of the scene list,
  each with the old file name and an option to reassign to an existing scene or delete

### Error States to Handle Gracefully

- Scene directory not found (misconfigured `config.toml`) → clear error on startup
- Scene file unreadable / unexpected format → log and skip, don't crash
- SQLite locked (shouldn't happen with single-writer, but) → retry with backoff
- Server unreachable from phone → frontend shows "offline" state, not blank screen

### Additional Tasks

- [ ] Add a `/api/config` endpoint that returns the configured scene directory path
  (so the UI can show it for debugging)
- [ ] Add a startup check that validates `scene_dir` exists and is readable
- [ ] Add a simple `GET /` redirect to the scene list for easy bookmarking
- [ ] Make the port configurable so it doesn't conflict with X32-Edit or other local
  services
- [ ] Write a `README.md` covering: installation, config, launchd setup, and how to
  find the app's local IP for phone access

---

## Implementation Order

The phases above are meant to be built sequentially, but within each phase start with
the smallest thing that produces visible output:

1. Parser that prints channel names to stdout from a real `.scn` file
2. Single `/api/scenes` endpoint returning file names only
3. Frontend list view hitting that endpoint
4. Add note storage and the note editor
5. Add EQ visualization
6. Add file watcher + SSE

This way you have something useful after Phase 1–3, and Phase 4 is pure polish.x
