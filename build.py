import json

names = ["workwear", "artisanal", "americana", "earthy", "minimal", "graphic", "knit", "outdoor"]

with open("data/buckets.json") as f:
    buckets = json.load(f)
with open("data/assigned.json") as f:
    assigned = json.load(f)

# one vibe per item, keyed by image (title as fallback)
vibe_by_image = {it["image"]: it.get("vibe") or "unknown" for it in assigned}
vibe_by_title = {it["title"]: it.get("vibe") or "unknown" for it in assigned}

# flat list so the page can group it three different ways
items = []
for i in range(len(buckets)):
    key = str(i)
    for it in buckets.get(key, []):
        vibe = vibe_by_image.get(it["image"]) or vibe_by_title.get(it["title"]) or "unknown"
        items.append({
            "title": it["title"],
            "price": it["price"],
            "image": it["image"],
            "bucket": key,
            "style": vibe,
        })

items_js = json.dumps(items, separators=(",", ":"))
names_js = json.dumps([n.capitalize() for n in names])
styles_js = json.dumps(names)
buckets_js = json.dumps([str(i) for i in range(len(buckets))])

template = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>buckets</title>
<style>
  :root {
    --bg: #111;
    --panel: #1a1a1a;
    --line: #2a2a2a;
    --line-strong: #444;
    --text: #eee;
    --muted: #999;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
  header { position: sticky; top: 0; z-index: 10; background: var(--bg); border-bottom: 1px solid #333; }
  .top { padding: 16px 16px 10px; }
  h1 { margin: 0 0 12px; font-size: 18px; font-weight: 600; letter-spacing: .5px; }
  nav { display: flex; gap: 8px; flex-wrap: wrap; }
  button {
    padding: 10px 18px; border: 1px solid var(--line-strong); background: #1c1c1c;
    color: var(--text); cursor: pointer; border-radius: 8px; font-size: 14px;
    transition: border-color .15s, background .15s, color .15s;
  }
  button:hover { border-color: #888; }
  button.active { background: #fff; color: #000; border-color: #fff; }
  button.empty { opacity: .38; }
  .count { opacity: .6; margin-left: 6px; }
  #modeNav { margin-bottom: 12px; }
  #modeNav button { font-weight: 600; }
  #outerNav { margin-bottom: 4px; }
  #crumb { opacity: .7; font-size: 12px; text-transform: uppercase; letter-spacing: .8px; padding: 8px 16px 8px; color: var(--muted); }
  #innerNav { padding: 0 16px 12px; border-top: 1px solid #222; padding-top: 12px; }
  #innerNav button { padding: 7px 12px; font-size: 13px; }
  #grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; padding: 16px; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; transition: border-color .15s, transform .15s; }
  .card:hover { border-color: var(--line-strong); transform: translateY(-2px); }
  .card img { width: 100%; aspect-ratio: 3/4; object-fit: cover; display: block; background: #222; }
  .card .info { padding: 10px; font-size: 13px; }
  .card .title { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .card .price { margin-top: 4px; opacity: .7; }
  .empty-msg { padding: 48px 16px; color: var(--muted); text-align: center; }
</style>
</head>
<body>
<header>
  <div class="top">
    <h1>buckets</h1>
    <nav id="modeNav"></nav>
    <nav id="outerNav"></nav>
  </div>
  <div id="crumb"></div>
  <nav id="innerNav"></nav>
</header>
<main id="grid"></main>
<script>
const ITEMS = __ITEMS__;
const NAMES = __NAMES__;
const STYLES = __STYLES__;
const BUCKETS = __BUCKETS__;

const modeNav = document.getElementById('modeNav');
const outerNav = document.getElementById('outerNav');
const innerNav = document.getElementById('innerNav');
const crumb = document.getElementById('crumb');
const grid = document.getElementById('grid');

const MODES = [
  { id: 'image-text', label: 'Image \u2192 Text' },
  { id: 'text', label: 'Text only' },
  { id: 'text-image', label: 'Text \u2192 Image' },
  { id: 'v0', label: 'v0' }
];

let mode = 'image-text';
let outer = null;
let inner = null;

function outerKeys() { return (mode === 'image-text' || mode === 'v0') ? BUCKETS : STYLES; }
function hasInner() { return mode === 'image-text' || mode === 'text-image'; }
function innerKeys() { return mode === 'text-image' ? BUCKETS : STYLES; }
function outerOf(it) { return (mode === 'image-text' || mode === 'v0') ? it.bucket : it.style; }
function innerOf(it) { return mode === 'text-image' ? it.bucket : it.style; }

function outerLabel(key) {
  return (mode === 'image-text' || mode === 'v0') ? 'Bucket ' + key : NAMES[STYLES.indexOf(key)];
}
function innerLabel(key) {
  return mode === 'text-image' ? 'Bucket ' + key : NAMES[STYLES.indexOf(key)];
}
function itemsInOuter(key) {
  return ITEMS.filter(it => outerOf(it) === key);
}
function itemsInOuterInner(okey, ikey) {
  return ITEMS.filter(it => outerOf(it) === okey && innerOf(it) === ikey);
}

for (const m of MODES) {
  const b = document.createElement('button');
  b.textContent = m.label;
  b.onclick = () => {
    modeNav.querySelectorAll('button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    setMode(m.id);
  };
  modeNav.appendChild(b);
}

function setMode(id) {
  mode = id;
  outer = outerKeys()[0];
  inner = hasInner() ? 'all' : null;
  renderOuterNav();
  renderInnerNav();
  renderGrid();
}

function renderOuterNav() {
  outerNav.innerHTML = '';
  for (const key of outerKeys()) {
    const b = document.createElement('button');
    b.innerHTML = outerLabel(key) + '<span class="count">(' + itemsInOuter(key).length + ')</span>';
    b.onclick = () => {
      outerNav.querySelectorAll('button').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      outer = key;
      inner = hasInner() ? 'all' : null;
      renderInnerNav();
      renderGrid();
    };
    outerNav.appendChild(b);
  }
  outerNav.children[0].classList.add('active');
}

function renderInnerNav() {
  innerNav.innerHTML = '';
  if (!hasInner()) {
    innerNav.style.display = 'none';
    return;
  }
  innerNav.style.display = 'flex';

  const allBtn = document.createElement('button');
  allBtn.innerHTML = 'All<span class="count">(' + itemsInOuter(outer).length + ')</span>';
  allBtn.onclick = () => {
    innerNav.querySelectorAll('button').forEach(x => x.classList.remove('active'));
    allBtn.classList.add('active');
    inner = 'all';
    renderGrid();
  };
  innerNav.appendChild(allBtn);

  for (const key of innerKeys()) {
    const n = itemsInOuterInner(outer, key).length;
    const b = document.createElement('button');
    b.innerHTML = innerLabel(key) + '<span class="count">(' + n + ')</span>';
    if (n === 0) b.classList.add('empty');
    b.onclick = () => {
      innerNav.querySelectorAll('button').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      inner = key;
      renderGrid();
    };
    innerNav.appendChild(b);
  }
  allBtn.classList.add('active');
}

function crumbLabel() {
  let s = MODES.find(m => m.id === mode).label + ' / ' + outerLabel(outer);
  if (hasInner()) s += ' / ' + (inner === 'all' ? 'All' : innerLabel(inner));
  return s;
}

function price(p) {
  const n = parseFloat(p);
  return '$' + (Number.isInteger(n) ? n : n.toFixed(2));
}

function renderGrid() {
  let items;
  if (!hasInner() || inner === 'all') {
    items = itemsInOuter(outer);
  } else {
    items = itemsInOuterInner(outer, inner);
  }

  crumb.textContent = crumbLabel();
  grid.innerHTML = '';

  if (items.length === 0) {
    const msg = document.createElement('div');
    msg.className = 'empty-msg';
    msg.textContent = 'no items';
    grid.appendChild(msg);
    return;
  }

  for (const item of items) {
    const card = document.createElement('div');
    card.className = 'card';

    const img = document.createElement('img');
    img.src = item.image;
    img.loading = 'lazy';
    img.alt = item.title;

    const info = document.createElement('div');
    info.className = 'info';

    const title = document.createElement('div');
    title.className = 'title';
    title.textContent = item.title;

    const p = document.createElement('div');
    p.className = 'price';
    p.textContent = mode === 'v0' ? '$' + item.price : price(item.price);

    info.append(title, p);
    card.append(img, info);
    grid.appendChild(card);
  }
}

setMode('image-text');
modeNav.children[0].classList.add('active');
</script>
</body>
</html>
"""

html = template.replace("__ITEMS__", items_js).replace("__NAMES__", names_js).replace("__STYLES__", styles_js).replace("__BUCKETS__", buckets_js)
with open("index.html", "w") as f:
    f.write(html)

print(f"wrote index.html ({len(html) / 1024:.0f} KB, {len(items)} items)")
