import { readFile, writeFile } from 'node:fs/promises';

const root = new URL('./', import.meta.url);
const read = name => readFile(new URL(name, root), 'utf8');
const snapshot = await read('v0-data.js');
const buckets = JSON.parse(snapshot.trim().replace(/^const V0_BUCKETS = /, '').replace(/;$/, ''));
const assigned = JSON.parse(await read('data/assigned.json'));
const byImage = new Map(assigned.map(item => [item.image, item]));
const byTitle = new Map(assigned.map(item => [item.title, item]));
let unmatched = 0;
const items = Object.entries(buckets).flatMap(([bucket, entries]) => entries.map(item => {
  const assignment = byImage.get(item.image) || byTitle.get(item.title);
  if (!assignment?.vibe) unmatched++;
  return { ...item, bucket, style: assignment?.vibe || 'unknown' };
}));
const html = await read('index.html');
if (!/^const ITEMS = .*;$/m.test(html)) throw new Error('Missing frontend data marker');
const data = JSON.stringify(items).replace(/</g, '\\u003c');
await writeFile(new URL('index.html', root), html.replace(/^const ITEMS = .*;$/m, () => `const ITEMS = ${data};`));
console.log(`Refreshed ${items.length} items in ${Object.keys(buckets).length} original clusters; ${unmatched} unassigned.`);
