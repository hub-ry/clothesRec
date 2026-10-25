# clothesRec v2.1 worklog

Branch `v2.1` (Ryan calls this version 2.1). Nothing here goes to `main`.
Scope: PLAN.md steps 1–4, with the site ready for step 5 (trying it with a friend).

Live: https://clothesrec.ryhub.dev (each person uses their own `/u/<token>` link).

## How it fits together

```
Shopify stores --collect.py--> data/clothesrec.db (SQLite) <--server.py--> browser (static/)
                                                    |
                          "Summarize my taste" --summarize.py--> DeepSeek Flash (images + ratings)
```

## Files

| File | What it does | Why it's like this |
|---|---|---|
| `v2/db.py` | Creates the SQLite tables (items, rejections, fetch_runs, people, feedback, summaries) and has the small helpers: upsert an item, set or clear feedback. | One file database, no server to run. An item's id is `domain:shopify_product_id`, so a refresh updates the same row and ratings stay attached when the price changes. |
| `v2/collect.py` | Pulls `products.json` from 4 Shopify stores (Kapital via haruyama365, Velour, Story mfg., 3sixteen), turns each product into an item (price = cheapest variant, sizes, in stock / sold out, currency from `meta.json`), and upserts it. Bad records go into `rejections` with a reason. | Plan step 1. These are real listings whose facts can be re-checked. Unknown stays unknown (no guessed currency or stock). A failed fetch only writes a failed `fetch_runs` row and never deletes items or marks them sold. Waits 1.5 s between requests and backs off on HTTP 429. |
| `v2/people.py` | `add 'Name'` prints a private link `/u/<token>`; `list` shows everyone. | Plan step 3 identity: a random unguessable link per person instead of an account system. Anyone with the link can act as that person, so keep it private. |
| `v2/server.py` | Python stdlib HTTP server (no framework). Serves the page for a valid token and a JSON API: items (paged, filterable), feedback PUT/DELETE, stats, rejections, summary preview/run, past summaries and corrections. | Every API call looks up the person from the token, so one person can never read or change another's ratings. Logs never print tokens, bodies, or query strings. |
| `v2/static/app.html`, `app.css`, `app.js` | The review grid: image, title, brand, source, price + currency, condition, sizes, stock badge, "checked X ago", original link. Buttons and keys: ← dislike, → like, ↑ love, Clear, optional note. Loads 48 at a time. Taste-summary panel and a rejected-records panel. | Plan step 2/3. Keys only act on the selected card and never while typing a note. Unrated means unknown. Responsive grid (`auto-fill, minmax(220px,1fr)`, one column under 480 px). |
| `v2/summarize.py` | Picks up to 12 rated examples (up to 4 each of love / like / dislike, newest first), builds the exact request (listing facts + notes as untrusted JSON, plus each image), calls DeepSeek Flash with JSON output and thinking off, stores the result, cost, and latency, and appends a line to `data/llm_calls.log`. | Plan step 4. Runs only when someone clicks the button. "Preview exact input" shows what will be sent. The prompt separates price/fit objections from style dislikes and makes every claim cite item ids. Spend guard: 1 call per person per minute, 30 per day. Summaries are editable; ratings stay the source of truth. |
| `v2/test_v2.py` | 10 offline unit tests (no network): stable ids on refresh, 429 retry, failed fetch keeps availability, missing currency, personal change/clear feedback, example selection, preview has no downloads, extra model keys dropped, unknown availability. | Run before every commit. |
| `deploy/clothesrec-v2.service` | systemd unit: runs `v2/server.py` on 127.0.0.1:8090 as ryanhubbart, with the DeepSeek key loaded from `~/.config/clothesrec/env`. | The existing cloudflared tunnel maps clothesrec.ryhub.dev to port 8090. No new tunnel or port is opened. |

The older files at the repo root (`scrape.py`, `embed.py`, `sort.py`, `assign.py`, ...) are v1 and untouched.

## Run and deploy (on hub)

```bash
cd ~/code/clothesRec-v2
python3 v2/collect.py --max-pages 1      # gentle refresh; drop the flag for full catalogs
python3 v2/people.py add 'Name'          # prints /u/<token>; share https://clothesrec.ryhub.dev/u/<token>
python3 v2/people.py list
python3 -m unittest v2/test_v2.py
sudo systemctl restart clothesrec-v2     # after code changes
journalctl -u clothesrec-v2 -f
```

First install: `sudo cp deploy/clothesrec-v2.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now clothesrec-v2`.
Data (`data/clothesrec.db`, `data/llm_calls.log`) is gitignored. The key file is chmod 600 and outside git.

## Key decisions (PM calls)

- Source: the 4 Shopify stores already scraped in v1. Listings only, no inspiration yet.
- Storage: SQLite. Identity: private token links.
- LLM: DeepSeek Flash (`deepseek-flash`), on demand only, images included, JSON output, thinking off.
- No framework, no build step, no extra dependencies (Python stdlib + plain JS).

## Who wrote what

- All code in `v2/` (5 commits) was written by GPT 6.1 sol (medium) through omp on hub, with omp subagents for the frontend and the summary module. Grok Bot (the PM) wrote the prompts, reviewed the diffs, and ran the checks.
- v2.1 follow-up fix (summary keeps only schema keys + its test): GPT 6.1 sol via omp.
- `WORKLOG.md` and `deploy/clothesrec-v2.service`: Grok Bot (PM), written by hand because they're small.

## LLM cost

One real summary call so far (Ryan's 6 ratings, 6 images): 2,488 input + 534 output tokens, **$0.00069**, **7.1 s**. It kept the "too expensive" note as a price objection, not a style dislike, and flagged that the notes were test data. At this rate 1,000 summaries cost about $0.70.

## Verified (Oct 24, 2026)

- Tests: `python3 -m unittest v2/test_v2.py` passes, 10 tests.
- Rate, change, clear, reload: checked through the API on both http://127.0.0.1:8090 and the live URL. Like, then love with a new note, then clear; every step read back from the server.
- Two people: Ryan loved an item while Test Friend disliked the same item. Each saw only their own rating, and clearing Ryan's left the friend's in place. An unknown token gets 404.
- Collector re-run (`--max-pages 1`, Oct 24 at 10:30 PM EDT): haruyama365 and Story succeeded (255 items refreshed, 2 of them rated). Velour and 3sixteen failed with HTTP 429. The catalog stayed at 2,277 items, and all saved feedback came through byte-for-byte unchanged.
- Spot check against the original pages: a Velour jeans listing and a Story cup listing match the live product data on price, sizes, stock, and image.
- Phone layout: headless Chrome screenshots at 390 px wide show one column with buttons that fit, and 1440 px shows five columns. The CSS uses an `auto-fill` grid plus a 480 px breakpoint.
- LLM: one real call; see the cost section above.

## Known limitations

- The stores rate-limit (HTTP 429) after a full crawl; a re-run soon after fails for that store, but data is kept. Use `--max-pages 1` for refreshes.
- Items that vanish from a store's feed are never marked sold; check "Checked X ago".
- Some 3sixteen products have vendor `0` in the store's own data, so the brand shows as "0".
- Listings only. No resale, Pinterest, or inspiration sources yet, and no recommendations (outside the plan's step 1–4 scope).
- Anyone with a link is that person. No login, no link revocation command (delete the row in `people` to revoke).
- The summary runs synchronously; the button waits up to ~60 s.
