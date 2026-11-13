const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/js/admin/calendar.js"), "utf8");

function element(dataset = {}, className = "") {
  const node = { dataset, className, children: [], parentElement: null, style: {},
    addEventListener() {}, setAttribute() {}, textContent: "", draggable: false,
    appendChild(child) { child.remove(); this.children.push(child); child.parentElement = this; return child; },
    append(...children) { children.forEach(child => this.appendChild(child)); },
    prepend(child) { child.remove(); this.children.unshift(child); child.parentElement = this; },
    remove() { if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(child => child !== this); this.parentElement = null; },
    querySelectorAll(selector) { return this.children.filter(child => child.classList.contains(selector.slice(1))); },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
  };
  node.classList = {
    contains(name) { return node.className.split(" ").includes(name); },
    add(...names) { node.className = [...new Set([...node.className.split(" "), ...names])].join(" "); },
    remove(...names) { node.className = node.className.split(" ").filter(name => !names.includes(name)).join(" "); },
    toggle(name, on) { if (on) this.add(name); else this.remove(name); },
  };
  Object.defineProperty(node, "innerHTML", { set() { node.children.forEach(child => { child.parentElement = null; }); node.children = []; } });
  return node;
}

function setup(assigned = []) {
  const weeks = [10, 11, 12].map((id, index) => ({id, name: id, start: "2026-11-" + (2 + index * 7), end: "2026-11-" + (8 + index * 7)}));
  const slots = weeks.flatMap(week => [1, 3].map(day => ({ requiredId: week.id * 10 + day, weekId: week.id, day, roomId: assigned.includes(week.id + ":" + day) ? 101 : null, weekName: week.id })));
  const request = {id: 101, occurrences: slots};
  const list = element({}, "required-list");
  const cells = [1, 3].map(day => element({room: "101", day: String(day)}, "schedule-cell"));
  const data = { session: "1", course: "Tin học", teacher: "GV", software: "[]", machines: "30", days: "3, 5", weekStart: "10", weekEnd: "12", date: "" };
  const pending = slots.find(slot => !slot.roomId);
  if (pending) list.appendChild(element({...data, requiredId: String(pending.requiredId)}, "required-item"));
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  get("weeks-data").textContent = JSON.stringify(weeks);
  get("calendar-requests-data").textContent = JSON.stringify([request]);
  get("scheduled-data").textContent = JSON.stringify(slots.filter(slot => slot.roomId).map(slot => ({
    MaYeuCau: slot.requiredId, MaTuanHoc: slot.weekId, Thu: slot.day + 2, MaPhong: 101,
    BuoiThucHanh: 1, TenHocPhan: "Tin học", TenGiangVien: "GV", MaPhanMem: [],
    MaTuanBatDau: 10, MaTuanKetThuc: 12,
  })));
  const document = {
    getElementById: get, createElement: () => element(), addEventListener() {},
    querySelectorAll(selector) {
      if (selector === ".required-item") return list.children;
      if (selector === ".schedule-cell") return cells;
      if (selector === ".scheduled-item") return cells.flatMap(cell => cell.children);
      return [];
    },
    querySelector(selector) {
      if (selector === ".required-list") return list;
      const day = selector.match(/data-day="(\d+)"/);
      return day ? cells.find(cell => cell.dataset.day === day[1]) : null;
    },
  };
  const context = vm.createContext({document, sessionStorage: {getItem() {return "1";}, setItem() {}}, window: {}, console, setTimeout() {}, clearInterval() {}});
  vm.runInContext(source, context);
  const run = code => vm.runInContext(code, context);
  const place = (week, day, all = false) => run('currentIndex = ' + (week - 10) + '; placeRequestOnCalendar(document.querySelectorAll(".schedule-cell").find(cell => Number(cell.dataset.day) === ' + day + '), waitingItems.get("101"), ' + day + ', ' + week + ', ' + !all + ');');
  const remove = (week, day, mode = "current_week") => run('currentIndex = ' + (week - 10) + '; executeDeleteSchedule("101", "' + mode + '", ' + day + ');');
  return { list, run, place, remove };
}

test("two weekdays in week 10 do not complete a three-week request", () => {
  const s = setup(); s.place(10, 1); s.place(10, 3);
  assert.equal(s.list.children.length, 1);
  assert.equal(s.run('getPendingOccurrences(101).length'), 4);
});

test("all Tuesdays plus one Thursday stay pending until every Thursday is assigned", () => {
  const s = setup(); s.place(10, 1, true); s.place(10, 3);
  assert.equal(s.list.children.length, 1);
  s.place(11, 3); assert.equal(s.list.children.length, 1);
  s.place(12, 3); assert.equal(s.list.children.length, 0);
  assert.equal(s.run('temporarySchedules.length'), 6);
});

test("removing just one occurrence restores a complete unsaved request", () => {
  const s = setup(); s.place(10, 1, true); s.place(10, 3, true);
  assert.equal(s.list.children.length, 0);
  s.remove(11, 3); assert.equal(s.list.children.length, 1);
  assert.equal(s.run('getPendingOccurrences(101).length'), 1);
  s.place(11, 3); assert.equal(s.list.children.length, 0);
});

test("saved rows with different IDs count toward the same request", () => {
  const s = setup(["10:1", "10:3", "11:1", "11:3", "12:1"]);
  assert.equal(s.list.children.length, 1);
  s.place(12, 3); assert.equal(s.list.children.length, 0);
});

test("removing one saved day restores only its missing occurrence, then can be filled", () => {
  const s = setup(["10:1", "10:3", "11:1", "11:3", "12:1", "12:3"]);
  s.remove(11, 3); assert.equal(s.list.children.length, 1);
  assert.equal(s.run('getPendingOccurrences(101).length'), 1);
  s.place(11, 3); assert.equal(s.list.children.length, 0);
  assert.equal(s.run('getAllSchedules().length'), 6);
});

test("removing a weekday in all weeks leaves the request waiting for all three", () => {
  const s = setup(["10:1", "10:3", "11:1", "11:3", "12:1", "12:3"]);
  s.remove(10, 3, "all"); assert.equal(s.list.children.length, 1);
  assert.equal(s.run('getPendingOccurrences(101).length'), 3);
  s.place(10, 3); assert.equal(s.list.children.length, 1);
  assert.equal(s.run('getPendingOccurrences(101).length'), 2);
  s.place(11, 3); s.place(12, 3); assert.equal(s.list.children.length, 0);
});


test("placements save each original row in its own week, without reusing a pending anchor", () => {
  const s = setup(); s.place(10, 1, true); s.place(10, 3, true);
  const rows = JSON.parse(s.run('JSON.stringify(temporarySchedules.map(({requiredId, weekId, day, existingSchedule}) => ({requiredId, weekId, day, existingSchedule})))'));
  assert.equal(new Set(rows.map(row => row.requiredId)).size, 6);
  rows.forEach(row => {
    assert.equal(Number(row.requiredId), row.weekId * 10 + row.day);
    assert.equal(row.existingSchedule, true);
  });
});

test("moving an assigned row changes its room without making the request complete early", () => {
  const s = setup(["10:1", "10:3"]);
  s.run('currentIndex = 0; renderScheduledRequests(); placeRequestOnCalendar({dataset: {room: "102"}}, document.querySelectorAll(".scheduled-item")[0], 1, 10, true);');
  assert.equal(s.list.children.length, 1);
  assert.equal(s.run('getAllSchedules().length'), 2);
  assert.equal(s.run('getPendingOccurrences(101).length'), 4);
});
