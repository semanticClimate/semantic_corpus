# Monitoring: live repository dashboard

Shows whether the pages that `semantic_corpus` queries are responding.

## Commands

```powershell
# Live dashboard → opens http://127.0.0.1:8766/
python -m semantic_corpus.monitoring serve

# Also run a real search (1 result per repository, once per hour)
python -m semantic_corpus.monitoring serve --deep

# Single check in the terminal (exit code 1 if anything is down)
python -m semantic_corpus.monitoring check
python -m semantic_corpus.monitoring check --deep --json
```

| Flag (`serve`) | Default | Purpose |
|---|---|---|
| `--port` | `8766` | Does not clash with the review viewer (8765) |
| `--interval` | `300` | Seconds between pings |
| `--deep` / `--deep-interval` | off / `3600` | Real search through the adapter |
| `--idle-timeout` | `600` | Pause checks when nobody has the dashboard open |
| `--history` | `temp/monitoring/health_history.jsonl` | History for the uptime strip |
| `--no-browser` | off | Do not open the browser |

## Architecture

```
RepositoryFactory ──► build_targets()        one target per class (aliases removed); UBA → exactas + fauba
                          │
                    Monitor (background thread)   checker.py
                      ├─ ping()               GET stream=True: headers only, 10 s timeout
                      ├─ search_once()        --deep: search_papers("climate", 1)
                      ├─ backoff ×2…×8        failing repositories are checked less often
                      ├─ idle pause
                      └─ JSONL history        + last 60 checks kept in memory
                          │
                    MonitorServer             server.py
                      ├─ GET /                dashboard.html
                      └─ GET /api/status      cached snapshot (never triggers checks)
                          │
                    dashboard.html            fetch every 15 s → table + uptime strip
```

**Statuses:** `up` · `slow` (> 3 s) · `warn` (4xx: answers but rejects us) ·
`degraded` (answers but search fails) · `down` (5xx, timeout, network or SSL error).

Each repository is checked at the same `base_url` its adapter uses. Europe PMC and arXiv are
API roots, so a minimal query is pinged instead (`PING_URL_OVERRIDES` in `checker.py`).
