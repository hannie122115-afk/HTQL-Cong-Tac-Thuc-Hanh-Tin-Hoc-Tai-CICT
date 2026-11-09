const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/js/auth/date-picker.js"), "utf8");

function fixture() {
  const listeners = new Map();
  const initialControl = {
    // After render(), the old month button is detached, so contains(target) is false.
    panel: { hidden: false, contains: () => false, matches: () => false },
    wrapper: { contains: () => false },
    trigger: { setAttribute() {}, focus() {} },
  };
  const document = {
    body: {}, querySelectorAll: () => [],
    addEventListener: (type, handler) => listeners.set(type, handler),
  };
  vm.runInNewContext(source.replace("let opened = null;", "let opened = initialControl;"), {
    initialControl, document, window: { addEventListener() {} },
    MutationObserver: class { observe() {} },
  });
  return { initialControl, click: listeners.get("click") };
}

test("clicking a month button detached by render keeps the calendar open", () => {
  const { initialControl, click } = fixture();
  const detachedMonthButton = {};
  click({ target: detachedMonthButton, composedPath: () => [detachedMonthButton, initialControl.panel] });
  assert.equal(initialControl.panel.hidden, false);
});

test("clicking the date field wrapper keeps the calendar open", () => {
  const { initialControl, click } = fixture();
  click({ target: {}, composedPath: () => [{}, initialControl.wrapper] });
  assert.equal(initialControl.panel.hidden, false);
});

test("clicking outside still closes the calendar", () => {
  const { initialControl, click } = fixture();
  click({ target: {}, composedPath: () => [{}] });
  assert.equal(initialControl.panel.hidden, true);
});
