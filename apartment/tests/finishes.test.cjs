const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
function method(name) {
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, name);
  const firstLine = source.slice(start, source.indexOf('\n', start));
  if (firstLine.endsWith('}')) return firstLine;
  return source.slice(start, source.indexOf('\n}', start) + 2);
}

const room = { floor: 'oak', floorColor: '#aabbcc' };
const calls = [];
const floor = {
  state: { rooms: { living: room } }, paint: { floor: 'tileStone', color: '#ff0000', floorTool: 'material' },
  pushHistory: () => calls.push('history'), applyFloors: () => calls.push('apply'), save: () => calls.push('save'),
  pulseAt() {}, toast() {}, dotHtml: () => '', icon: () => '', floorTex: () => '', texThumb: () => '',
};
vm.createContext(floor);
vm.runInContext(method('setFloor'), floor);
floor.setFloor('living');
assert.equal(room.floor, 'tileStone');
assert.equal(room.floorColor, '#aabbcc');
floor.paint.floorTool = 'color';
floor.setFloor('living');
assert.equal(room.floor, 'tileStone');
assert.equal(room.floorColor, '#ff0000');
const count = calls.length;
floor.setFloor('living');
assert.equal(calls.length, count);
// Follow the canvas tap route through a real floor hit, including the wall palette.
floor.floorMeshes = [{}]; floor.wallMeshes = []; floor.pickables = [];
floor.pick = () => ({ object: { userData: { room: 'living' } }, point: { x: 1, y: 0, z: 2 } });
floor.isPaintMode = () => true; floor.activeTab = 'floor';
vm.runInContext(['paintFloorAt', 'paintWallAt', 'handleTap'].map(method).join('\n'), floor);
room.floorColor = undefined;
floor.paint.color = '#00ff00'; floor.paint.floorTool = 'color';
floor.handleTap(30, 40, null);
assert.equal(room.floorColor, '#00ff00');
floor.activeTab = 'walls'; floor.paint.color = '#ff0000';
floor.handleTap(30, 40, null);
assert.equal(room.floorColor, '#ff0000');
floor.activeTab = 'floor'; floor.paint.floorTool = 'material'; floor.paint.floor = 'tileWhite';
floor.handleTap(30, 40, null);
assert.equal(room.floor, 'tileWhite');
assert.equal(room.floorColor, '#ff0000');

class Target {
  constructor() { this.listeners = {}; this.style = {}; }
  addEventListener(type, fn) { (this.listeners[type] ??= new Set()).add(fn); }
  removeEventListener(type, fn) { this.listeners[type]?.delete(fn); }
  fire(type, event = {}) { for (const fn of [...(this.listeners[type] || [])]) fn({ type, ...event }); }
  setPointerCapture() {}
}
const el = new Target(), window = new Target(), ended = [];
const drag = {
  window, paintPointer: null, Math, setTimeout() {}, startPaintDrag() {}, movePaintDrag() {},
  endPaintDrag: (...args) => ended.push(args),
};
vm.createContext(drag);
vm.runInContext(method('makePaintDrag'), drag);
drag.makePaintDrag(el, { kind: 'color', value: '#fff' });
el.fire('pointerdown', { button: 0, pointerId: 7, clientX: 0, clientY: 0 });
el.fire('pointerdown', { button: 0, pointerId: 8, clientX: 0, clientY: 0 });
window.fire('pointermove', { pointerId: 7, clientX: 20, clientY: 0 });
el.fire('lostpointercapture', { pointerId: 7 });
assert.equal(ended.length, 1);
assert.equal(ended[0][0], false);
window.fire('pointerup', { pointerId: 7 });
assert.equal(ended.length, 1);
el.fire('pointerdown', { button: 0, pointerId: 9, clientX: 0, clientY: 0 });
window.fire('pointermove', { pointerId: 9, clientX: 20, clientY: 0 });
window.fire('pointerup', { pointerId: 9, clientX: 20, clientY: 0 });
assert.equal(ended.length, 2);
assert.equal(ended[1][0], true);

const buttons = { btnUndo: { disabled: true } };
const state = { rooms: { living: { wall: '#fff', finish: 'paint', floor: 'oak', floorColor: '#ffffff' } }, walls: {} };
const hist = {
  state, items: [], demoActive: false, history: [], KEY: 'test', DEFS: {},
  DEFAULT_ROOMS: { living: { wall: '#fff', finish: 'paint', floor: 'oak' } },
  $: (q) => buttons[q.slice(1)], store: { get: () => null }, defaultState: () => ({}),
  save() {}, toast() {}, icon: () => '', applySnapshot(s) { hist.state.rooms = s.rooms; hist.state.walls = s.walls; },
};
vm.createContext(hist);
vm.runInContext(['serialize', 'pushHistory', 'undo', 'loadState'].map(method).join('\n'), hist);
hist.pushHistory(); hist.state.rooms.living.floorColor = '#aa0000';
hist.pushHistory(); hist.state.rooms.living.floor = 'tileStone';
const saved = JSON.stringify(hist.serialize());
assert.equal(JSON.parse(saved).rooms.living.floorColor, '#aa0000');
hist.undo(); assert.equal(hist.state.rooms.living.floor, 'oak');
assert.equal(hist.state.rooms.living.floorColor, '#aa0000');
hist.undo(); assert.equal(hist.state.rooms.living.floorColor, '#ffffff');
hist.store.get = () => saved;
assert.equal(hist.loadState().rooms.living.floorColor, '#aa0000');
console.log('finishes: floor state, history, and drag cleanup passed');
