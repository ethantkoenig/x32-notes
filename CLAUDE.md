# x32-lib

Web app for annotating Behringer X32 mixer scene files (.scn, .snp, .chn). Parses binary/text scene files, displays channel EQ/dynamics graphs, and stores user notes in a local SQLite database.

## Running the server

```bash
uv run python -m server.main
```

Runs on `http://localhost:8765` (configured in `config.toml`). The frontend is served as static files from `frontend/`. Restart required after backend changes; frontend changes take effect on browser refresh.

## Tests

```bash
uv run pytest
```

All tests are in `tests/`. `test_parser.py` covers scene/channel file parsing; `test_api.py` covers HTTP endpoints. Use `uv run playwright install chromium` once before running UI tests.

## Project layout

```
server/
  main.py          FastAPI app factory, lifespan (DB init + file watcher)
  config.py        Config dataclass; reads config.toml ([server] and [x32] sections)
  parser/
    scene.py       Core parser — handles .scn/.snp (multi-channel) and .chn (single-channel)
    parameters.py  Dataclasses: Channel, EQ, EQBand, Compressor, Gate
    channel.py     Thin wrapper: parse_scene → first channel (used for .chn files)
  routers/
    scenes.py      GET /api/scenes, GET /api/scenes/{path}
    notes.py       GET/POST/DELETE /api/notes/{path}
    events.py      GET /api/events  (SSE, fires on file-system changes)
    health.py      GET /api/health
  db/
    database.py    init_db — creates notes table
    notes.py       get_note, upsert_note, delete_note, list_all_notes
  watcher.py       watchdog observer; broadcasts to SSE subscribers on scene-dir changes

frontend/
  index.html       Scene list (Alpine component: sceneList)
  scene.html       Multi-channel scene view (Alpine component: sceneDetail)
  channel.html     Single .chn channel view (Alpine component: channelDetail)
  js/
    utils.js       x32Color, formatDb, formatDate, encodePath
    api.js         api.getScenes(), api.getScene(path), api.saveNote(path, note)
    app.js         All Alpine components registered here
  components/
    eq-curve.js    drawEQCurve(canvas, eq)    — small EQ graph used in scene.html
    eq-detail.js   drawDetailedEQ(canvas, eq) — large labelled EQ graph for channel.html
    dyn-graph.js   drawCompressor(canvas, comp), drawGate(canvas, gate)
  css/app.css      Single stylesheet; CSS variables for theming
```

## Key data model

**EQ** (`parameters.py`): `enabled`, `bands: list[EQBand | None]`, `low_cut_enabled`, `low_cut_freq`. Low-cut comes from the `/preamp` line (not `/eq`), parsed as 24 dB/oct HPF (two cascaded 2nd-order Butterworth biquads, Q = 0.5412 and 1.3066).

**EQBand** types: `PEQ`, `VEQ`, `HShv`, `LShv`, `HCut`, `LCut`. Rendered via RBJ biquad cookbook formulas in `eq-curve.js`.

**Compressor**: threshold, ratio, knee (integer 0–5; multiply by 3 for knee width in dB), makeup, attack, hold, release, mode/det/env.

**Gate**: type (`GATE`, `EXP2`, `EXP4`, `DUCK`), threshold, range, attack, hold, release.

## File format notes

**.scn / .snp** lines look like:
```
/ch/01/config "Name" 1 CY 1
/ch/01/eq ON
/ch/01/eq/1 PEQ 164.4 -3.75 1.8
/ch/01/preamp +0.0 OFF OFF 24 79
```
Parsed by `_CH_RE = r"^/ch/(\d{2})/(.+)$"`.

**.chn** lines have no `/ch/01/` prefix:
```
/config "Dave" 50 YE
/eq ON
/eq/1 PEQ 376.7 -14.7 7.1
/preamp +0.0 OFF ON 24 121
```
Parsed when `path.suffix == ".chn"` using `_CHN_RE`, treated as channel index 1.

**Frequency notation**: `1k39` means 1390 Hz (parsed by `parse_freq`). `parse_db` converts `-oo` to `-inf`.

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/scenes` | Returns `{scenes, orphaned_notes}` |
| GET | `/api/scenes/{path}` | Returns scene with `channels` dict (key = channel index as string), `note`, `last_modified` |
| POST | `/api/notes/{path}` | Body: `{"note": "..."}` |
| GET | `/api/events` | SSE stream; each message triggers a scene-list reload |

## Frontend routing

- `.scn` / `.snp` → `scene.html?path=...`
- `.chn` → `channel.html?path=...`

Routing is in `openScene()` in `app.js`. Alpine.js 3.14.1 loaded from CDN; components registered before Alpine initialises (in `app.js`, before the `defer` script tag).

## Canvas drawing pattern

All canvas functions follow the same pattern: read `getBoundingClientRect()` for CSS size, set `canvas.width/height` in device pixels, call `ctx.scale(dpr, dpr)`, then draw in CSS pixels. **Must be called after the element is in the DOM** — always pair with `await this.$nextTick()` after setting `loading = false`, not before.

## Config

`config.toml` (gitignored in production; present in repo for dev):
```toml
[server]
host = "0.0.0.0"
port = 8765

[x32]
scene_dir = "/path/to/scenes"
```

Default `scene_dir` if absent: `~/Documents/X32Edit/Scenes`.
