import json

names = ["workwear", "artisanal", "americana", "earthy", "minimal", "graphic", "knit", "outdoor"]

with open("data/buckets.json") as f:
    buckets = json.load(f)

# keep buckets in numeric order for a stable file
ordered = {str(i): buckets[str(i)] for i in range(len(buckets))}
data = json.dumps(ordered, separators=(",", ":"))

labels = json.dumps([n.capitalize() for n in names])

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
  header { position: sticky; top: 0; z-index: 10; background: var(--bg); padding: 16px 16px 12px; border-bottom: 1px solid #333; }
  h1 { margin: 0 0 12px; font-size: 18px; font-weight: 600; letter-spacing: .5px; }
  nav { display: flex; gap: 8px; flex-wrap: wrap; }
  button {
    padding: 10px 18px; border: 1px solid var(--line-strong); background: #1c1c1c;
    color: var(--text); cursor: pointer; border-radius: 8px; font-size: 14px;
    transition: border-color .15s, background .15s, color .15s;
  }
  button:hover { border-color: #888; }
  button.active { background: #fff; color: #000; border-color: #fff; }
  .count { opacity: .6; margin-left: 6px; }
  #grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; padding: 16px; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; transition: border-color .15s, transform .15s; }
  .card:hover { border-color: var(--line-strong); transform: translateY(-2px); }
  .card img { width: 100%; aspect-ratio: 3/4; object-fit: cover; display: block; background: #222; }
  .card .info { padding: 10px; font-size: 13px; }
  .card .title { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .card .price { margin-top: 4px; opacity: .7; }
</style>
</head>
<body>
<header>
  <h1>buckets</h1>
  <nav id="nav"></nav>
</header>
<main id="grid"></main>
<script>
const BUCKETS = __BUCKETS__;
const NAMES = __NAMES__;

const nav = document.getElementById('nav');
const grid = document.getElementById('grid');

for (const key in BUCKETS) {
  const b = document.createElement('button');
  b.innerHTML = NAMES[key] + '<span class="count">(' + BUCKETS[key].length + ')</span>';
  b.onclick = () => {
    nav.querySelectorAll('button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    render(key);
  };
  nav.appendChild(b);
}

function price(p) {
  const n = parseFloat(p);
  return '$' + (Number.isInteger(n) ? n : n.toFixed(2));
}

function render(key) {
  grid.innerHTML = '';
  for (const item of BUCKETS[key]) {
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
    p.textContent = price(item.price);

    info.append(title, p);
    card.append(img, info);
    grid.appendChild(card);
  }
}

render(Object.keys(BUCKETS)[0]);
nav.children[0].classList.add('active');
</script>
</body>
</html>
"""

html = template.replace("__BUCKETS__", data).replace("__NAMES__", labels)
with open("index.html", "w") as f:
    f.write(html)

total = sum(len(v) for v in ordered.values())
print(f"wrote index.html ({len(html) / 1024:.0f} KB, {len(ordered)} buckets, {total} items)")
