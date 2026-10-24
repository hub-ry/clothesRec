'use strict';

const $ = id => document.getElementById(id);
const token = location.pathname.split('/').filter(Boolean).pop();
const base = `/api/u/${encodeURIComponent(token || '')}`;
const grid = $('grid');
let items = [], total = 0, offset = 0, generation = 0, loading = false;
let selected = null, pending = 0;
const feedbackCache = new Map();
const queues = new Map();
const reactions = ['dislike', 'like', 'love'];

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function error(err) { $('error').textContent = err.message || String(err); $('error').hidden = false; }
async function api(path, options = {}) {
  const response = await fetch(base + path, { ...options, headers: { 'Content-Type': 'application/json' } });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
  return data;
}
function safeURL(value) {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url : null; }
  catch { return null; }
}
function relative(value) {
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return 'unknown';
  const minutes = Math.max(0, Math.floor((Date.now() - time) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hr ago`;
  return `${Math.floor(minutes / 1440)} days ago`;
}
function select(id, scroll = false) {
  selected = id;
  for (const card of grid.children) card.classList.toggle('selected', card.dataset.id === id);
  if (scroll) Array.from(grid.children).find(card => card.dataset.id === id)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}
function updateFeedback(card, item) {
  card.querySelector('.rating').textContent = item.feedback ? `Rated: ${item.feedback.reaction}` : 'Unrated';
  for (const button of card.querySelectorAll('[data-reaction]')) button.setAttribute('aria-pressed', String(button.dataset.reaction === item.feedback?.reaction));
}
function saveFeedback(item, card, reaction, note) {
  const status = card.querySelector('.save-status');
  if (note.length > 500) { status.textContent = 'Keep notes to 500 characters.'; return; }
  pending++;
  if ($('filter').value !== 'all') { generation++; loading = false; }
  status.textContent = 'Saving…';
  const previous = queues.get(item.id) || Promise.resolve();
  const job = previous.then(async () => {
    const currentReaction = reaction === undefined ? item.feedback?.reaction : reaction;
    if (reaction === undefined && !currentReaction) {
      status.textContent = 'Choose a reaction to save this note.';
      return;
    }
    const response = await api(`/feedback/${encodeURIComponent(item.id)}`, currentReaction ? { method: 'PUT', body: JSON.stringify({ reaction: currentReaction, note }) } : { method: 'DELETE' });
    const feedback = currentReaction ? response : null;
    item.feedback = feedback;
    feedbackCache.set(item.id, feedback);
    const visibleItem = items.find(value => value.id === item.id);
    if (visibleItem) visibleItem.feedback = feedback;
    updateFeedback(card, item);
    status.textContent = 'Saved';
  }).catch(err => { status.textContent = 'Not saved. Try again.'; error(err); }).finally(() => {
    pending--;
    if (queues.get(item.id) === job) queues.delete(item.id);
    if (!pending) {
      refreshStats().catch(error);
      if ($('filter').value !== 'all') resetCatalog();
      else updateCatalogStatus();
    }
  });
  queues.set(item.id, job);
}
function renderCard(item) {
  const card = node('article', undefined, 'card');
  card.dataset.id = item.id;
  card.addEventListener('click', () => select(item.id));
  const picture = node('div', undefined, 'picture');
  const imageURL = (item.image_urls || []).map(safeURL).find(Boolean) || safeURL(item.image_url);
  if (imageURL) {
    if (item.source?.toLowerCase().includes('shopify') || imageURL.hostname === 'cdn.shopify.com' || imageURL.hostname.endsWith('.shopify.com') || imageURL.pathname.includes('/cdn/shop/')) imageURL.searchParams.set('width', '400');
    const image = node('img');
    image.loading = 'lazy'; image.decoding = 'async'; image.alt = item.title || 'Clothing item';
    image.addEventListener('error', () => { picture.replaceChildren(node('span', 'No image')); }, { once: true });
    image.src = imageURL.href; picture.append(image);
  } else picture.append(node('span', 'No image'));
  const body = node('div', undefined, 'card-body');
  body.append(node('span', item.kind === 'listing' ? 'Listing' : 'Inspiration · not inventory', 'badge'), node('h3', item.title || 'Untitled item'));
  body.append(node('p', `${item.brand || 'Brand unknown'} · ${item.source || 'Source unknown'}`, 'meta'));
  if (item.kind === 'listing') {
    const price = item.price === null || item.price === undefined || item.price === '' ? 'Price unknown' : `Price: ${item.price}`;
    body.append(node('p', `${price} · ${item.currency || 'Currency unknown'}`));
    body.append(node('p', `Condition: ${item.condition || 'unknown'} · Sizes: ${item.sizes?.length ? item.sizes.join(', ') : 'unknown'}`, 'meta'));
    body.append(node('span', item.available === 1 ? 'In stock' : item.available === 0 ? 'Sold out' : 'Availability unknown', 'badge'));
    body.append(node('p', `Checked: ${relative(item.last_checked_at)}`, 'meta'));
  }
  const original = safeURL(item.url);
  if (original) { const link = node('a', 'View original'); link.href = original.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; body.append(link); }
  else body.append(node('p', 'Original link unavailable', 'meta'));
  body.append(node('p', '', 'rating'));
  const controls = node('div', undefined, 'reactions');
  const note = node('textarea'); note.maxLength = 500; note.rows = 2; note.value = item.feedback?.note || '';
  note.setAttribute('aria-label', `Note for ${item.title || 'item'}`);
  for (const reaction of reactions) {
    const button = node('button', `${{ dislike: '👎', like: '👍', love: '❤️' }[reaction]} ${reaction}`); button.type = 'button'; button.dataset.reaction = reaction;
    button.addEventListener('click', () => saveFeedback(item, card, reaction, note.value)); controls.append(button);
  }
  const clear = node('button', 'Clear'); clear.type = 'button';
  clear.addEventListener('click', () => { note.value = ''; saveFeedback(item, card, null, ''); }); controls.append(clear);
  const label = node('label', 'Note (500 characters max)', 'note-label'); label.append(note);
  const saveNote = () => {
    if (note.value === (item.feedback?.note || '')) return;
    if (!item.feedback && !queues.has(item.id)) { card.querySelector('.save-status').textContent = 'Choose a reaction to save this note.'; return; }
    saveFeedback(item, card, undefined, note.value);
  };
  note.addEventListener('blur', saveNote);
  note.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); note.blur(); } });
  body.append(controls, label, node('p', '', 'save-status')); card.append(picture, body); updateFeedback(card, item);
  return card;
}
function updateCatalogStatus() {
  $('catalog-status').textContent = `${items.length} of ${total} shown`;
  $('more').hidden = offset >= total;
  $('more').disabled = loading || pending > 0;
  $('more').textContent = loading ? 'Loading…' : 'Load 48 more';
}
async function loadMore() {
  if (loading || pending || offset >= total && offset !== 0) return;
  const version = generation; const filter = $('filter').value;
  loading = true; updateCatalogStatus();
  try {
    const result = await api(`/items?offset=${offset}&limit=48&filter=${encodeURIComponent(filter)}`);
    if (version !== generation) return;
    total = result.total; offset += result.items.length;
    for (const item of result.items) {
      if (items.some(existing => existing.id === item.id)) continue;
      if (feedbackCache.has(item.id)) item.feedback = feedbackCache.get(item.id);
      items.push(item); grid.append(renderCard(item));
    }
    if (!items.some(item => item.id === selected)) selected = items[0]?.id || null;
    select(selected);
    if (!result.items.length) offset = total;
  } catch (err) { if (version === generation) error(err); }
  finally { if (version === generation) { loading = false; updateCatalogStatus(); } }
}
function resetCatalog() {
  generation++; loading = false; items = []; offset = 0; total = 0; grid.replaceChildren();
  $('catalog-status').textContent = 'Loading…';
  loadMore();
}
async function refreshStats() {
  const stats = await api('/stats');
  const runs = Array.isArray(stats.fetch_runs) ? stats.fetch_runs.map(run => `${run.source || 'Unknown source'}: ${run.ok ? 'ok' : 'failed'} (${relative(run.finished_at || run.started_at)})${run.error ? `: ${run.error}` : ''}`).join('; ') || 'none' : stats.fetch_runs;
  $('stats').textContent = `Dislike ${stats.dislike} · Like ${stats.like} · Love ${stats.love} · Catalog ${stats.catalog_size} · Last checked ${relative(stats.last_checked_at)} · Fetch runs: ${runs}`;
  $('rejection-count').textContent = `Rejected records (${stats.rejection_count})`;
}
function json(value) { if (typeof value !== 'string') return value; try { return JSON.parse(value); } catch { return value; } }
function summaryCard(row) {
  const section = node('article', undefined, 'summary-record');
  section.append(node('h3', `Summary #${row.id}`));
  section.append(node('p', `Created ${row.created_at || 'unknown'} · Model ${row.model || 'unknown'} · Prompt ${row.prompt_version || 'unknown'}`, 'meta'));
  section.append(node('p', `Cost: ${row.cost_usd == null ? 'unknown' : `$${row.cost_usd}`} · Latency: ${row.latency_ms == null ? 'unknown' : `${row.latency_ms} ms`} · Input/output tokens: ${row.input_tokens ?? 'unknown'} / ${row.output_tokens ?? 'unknown'}`, 'meta'));
  section.append(node('p', `Feedback IDs: ${JSON.stringify(json(row.feedback_ids))}`));
  if (row.error) section.append(node('p', `Summary failed: ${row.error}`));
  section.append(node('h4', 'Inferences and supporting IDs'), node('pre', JSON.stringify(json(row.result_json), null, 2) ?? 'No result'));
  const label = node('label', 'Your correction');
  const correction = node('textarea'); correction.value = row.edited_text || ''; correction.rows = 4; label.append(correction);
  const button = node('button', 'Save correction'); button.type = 'button';
  const status = node('p', '', 'save-status');
  button.addEventListener('click', async () => {
    button.disabled = true; status.textContent = 'Saving…';
    try { const saved = await api(`/summaries/${encodeURIComponent(row.id)}`, { method: 'PUT', body: JSON.stringify({ edited_text: correction.value }) }); correction.value = saved.edited_text || ''; status.textContent = 'Correction saved'; }
    catch (err) { status.textContent = 'Not saved'; error(err); }
    finally { button.disabled = false; }
  });
  section.append(label, button, status); return section;
}
async function history() {
  const rows = await api('/summaries');
  $('summaries').replaceChildren(...rows.map(summaryCard));
  if (!rows.length) $('summaries').append(node('p', 'No summaries yet.'));
}
$('filter').addEventListener('change', resetCatalog);
$('more').addEventListener('click', loadMore);
if ('IntersectionObserver' in window) new IntersectionObserver(entries => { if (entries.some(entry => entry.isIntersecting) && offset < total) loadMore(); }, { rootMargin: '300px' }).observe($('sentinel'));
document.addEventListener('keydown', event => {
  if (event.target.closest('input, textarea, select, [contenteditable="true"]') || event.altKey || event.ctrlKey || event.metaKey) return;
  const index = items.findIndex(item => item.id === selected);
  if (index < 0) return;
  const reaction = { ArrowLeft: 'dislike', ArrowRight: 'like', ArrowUp: 'love' }[event.key];
  if (reaction) {
    event.preventDefault();
    if (event.repeat) return;
    const card = grid.children[index];
    saveFeedback(items[index], card, reaction, card.querySelector('textarea').value);
  } else if (['ArrowDown', 'j', 'k'].includes(event.key)) {
    event.preventDefault();
    const next = event.key === 'k' ? index - 1 : index + 1;
    if (items[next]) select(items[next].id, true);
    else if (next >= items.length) loadMore();
  }
});
$('preview').addEventListener('click', async () => {
  $('preview').disabled = true;
  try { const data = await api('/summary/preview'); $('preview-json').textContent = JSON.stringify(data, null, 2); $('preview-panel').open = true; }
  catch (err) { error(err); }
  finally { $('preview').disabled = false; }
});
$('run').addEventListener('click', async () => {
  $('run').disabled = true; $('summary-status').textContent = 'Sending selected feedback and images to DeepSeek…';
  try { const row = await api('/summary', { method: 'POST', body: '{}' }); $('latest-summary').replaceChildren(summaryCard(row)); $('summary-status').textContent = row.error ? 'Summary failed. See details below.' : 'Summary saved. Review its inferences below.'; await history(); }
  catch (err) { $('summary-status').textContent = 'Summary failed.'; error(err); }
  finally { $('run').disabled = false; }
});
$('history').addEventListener('click', () => history().catch(error));
$('rejections-panel').addEventListener('toggle', async () => {
  if (!$('rejections-panel').open) return;
  try {
    const rows = await api('/rejections');
    $('rejections').replaceChildren(...rows.map(row => node('pre', JSON.stringify(row, null, 2))));
    if (!rows.length) $('rejections').append(node('p', 'No rejected records.'));
  } catch (err) { error(err); }
});
refreshStats().catch(error);
history().catch(error);
resetCatalog();
