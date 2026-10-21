import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

class Element {
  children = [];
  style = {};
  attributes = {};
  classes = new Set();
  classList = {
    add: name => this.classes.add(name),
    remove: name => this.classes.delete(name),
    contains: name => this.classes.has(name),
    toggle: (name, selected) => selected ? this.classes.add(name) : this.classes.delete(name)
  };
  set innerHTML(value) { this.children = []; }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.append(child); }
  querySelectorAll() { return this.children; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener() {}
}

const read = name => readFileSync(new URL(name, import.meta.url), 'utf8');
const nodes = {};
const context = vm.createContext({ document: {
  getElementById: id => nodes[id] ??= new Element(),
  createElement: () => new Element()
} });
vm.runInContext(read('v0-data.js'), context);
vm.runInContext(read('index.html').match(/<script>([\s\S]*?)<\/script>/)[1], context);
const run = source => vm.runInContext(source, context);

test('cluster membership and order match the saved v0 snapshot', () => {
  run(`setMode('image-text')`);
  for (const key of run('Object.keys(V0_BUCKETS)')) {
    assert.equal(run(`JSON.stringify(itemsInOuter('${key}').map(({style, ...item}) => item))`),
      run(`JSON.stringify(V0_ITEMS.filter(item => item.bucket === '${key}'))`));
  }
});

test('forward and reverse groupings have identical intersections', () => {
  for (const bucket of run('Object.keys(V0_BUCKETS)')) {
    for (const vibe of run('STYLES')) {
      run(`setMode('image-text')`);
      const forward = run(`JSON.stringify(itemsInOuterInner('${bucket}', '${vibe}'))`);
      run(`setMode('text-image')`);
      assert.equal(run(`JSON.stringify(itemsInOuterInner('${vibe}', '${bucket}'))`), forward);
    }
  }
});

test('all modes and filter buttons render accurate counts', () => {
  const expected = run('V0_ITEMS.length');
  for (const mode of ['v0', 'image-text', 'text', 'text-image']) {
    run(`setMode('${mode}')`);
    let total = 0;
    for (const button of [...nodes.outerNav.children]) {
      button.onclick();
      total += run('itemsInOuter(outer).length');
      assert.equal(nodes.grid.children.length, run('itemsInOuter(outer).length') || 1);
      if (nodes.innerNav.style.display === 'none') continue;
      for (const filter of [...nodes.innerNav.children]) {
        filter.onclick();
        const count = run(`inner === 'all' ? itemsInOuter(outer).length : itemsInOuterInner(outer, inner).length`);
        assert.equal(nodes.grid.children.length, count || 1);
      }
    }
    assert.equal(total, expected);
  }
});

test('every snapshot item has the saved vibe assignment', () => {
  const assigned = JSON.parse(read('data/assigned.json'));
  const byImage = new Map(assigned.map(item => [item.image, item.vibe]));
  const byTitle = new Map(assigned.map(item => [item.title, item.vibe]));
  for (const item of run('CLUSTER_ITEMS')) {
    assert.equal(item.style, byImage.get(item.image) || byTitle.get(item.title) || 'unknown');
  }
});
