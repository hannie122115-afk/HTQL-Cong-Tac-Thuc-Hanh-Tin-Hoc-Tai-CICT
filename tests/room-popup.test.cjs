const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/js/admin/room.js"), "utf8");

function element(dataset = {}) {
  const handlers = new Map();
  const classes = new Set();
  return {
    dataset, hidden: true, disabled: false, textContent: "", action: "",
    classList: { add: name => classes.add(name), remove: name => classes.delete(name), contains: name => classes.has(name) },
    addEventListener(name, callback) {
      if (!handlers.has(name)) handlers.set(name, []);
      handlers.get(name).push(callback);
    },
    emit(name, event = {}) { for (const callback of handlers.get(name) || []) callback(event); },
    setAttribute(name, value) { this[name] = value; },
    getAttribute(name) { return this[name] || null; },
    querySelector() { return null; },
    handlerCount(name) { return (handlers.get(name) || []).length; },
  };
}

function setup({ loading = false, addControls = true, missingPopup = false } = {}) {
  const nodes = new Map();
  for (const id of ["room-page", "popup-error", "popup-error-message", "popup-error-close",
    "popup-success", "popup-delete-room", "delete-room-form", "delete-room-name",
    "delete-room-confirm", "delete-room-cancel"]) nodes.set(id, element());
  if (missingPopup) nodes.delete("popup-delete-room");
  if (addControls) for (const id of ["room-add-act", "room-add-container", "room-add-form", "cancel-add-config-btn"]) nodes.set(id, element());
  const document = element();
  document.readyState = loading ? "loading" : "complete";
  document.getElementById = id => nodes.get(id) || null;
  const alerts = [];
  const context = vm.createContext({ document, window: { alert: text => alerts.push(text) }, setTimeout() {} });
  const run = () => vm.runInContext(source, context);
  const click = (id = "102", icon = false) => {
    const button = element({ id, roomName: "Phòng 102" });
    button.closest = () => button;
    const target = icon ? { closest: () => button } : button;
    const event = { target, preventDefault() { this.prevented = true; } };
    document.emit("click", event);
    return event;
  };
  run();
  return { document, nodes, alerts, click, run };
}

test("clicking Delete directly opens #popup-delete-room and sets its POST target", () => {
  const { nodes, click } = setup();
  assert.equal(click().prevented, true);
  assert.equal(nodes.get("popup-delete-room").classList.contains("show"), true);
  assert.equal(nodes.get("popup-delete-room").hidden, false);
  assert.equal(nodes.get("delete-room-form").action, "/admin/room/102/delete");
  assert.equal(nodes.get("delete-room-name").textContent, "Phòng 102");
});

test("missing Add Room controls cannot prevent the Delete popup from opening", () => {
  const { nodes, click } = setup({ addControls: false });
  click();
  assert.equal(nodes.get("popup-delete-room").classList.contains("show"), true);
});

test("binding waits for DOMContentLoaded when the script loads before the page", () => {
  const { nodes, document, click } = setup({ loading: true });
  assert.equal(document.handlerCount("click"), 0);
  document.readyState = "complete";
  document.emit("DOMContentLoaded");
  click();
  assert.equal(nodes.get("popup-delete-room").classList.contains("show"), true);
});

test("clicking the trash icon and buttons added later both work", () => {
  const { nodes, click } = setup();
  click("104", true);
  assert.equal(nodes.get("delete-room-form").action, "/admin/room/104/delete");
});

test("loading the script twice does not duplicate click handlers", () => {
  const { document, run } = setup();
  run();
  assert.equal(document.handlerCount("click"), 1);
});

test("missing popup and invalid room IDs show an error instead of failing silently", () => {
  const missing = setup({ missingPopup: true });
  missing.click();
  assert.equal(missing.nodes.get("popup-error").classList.contains("show"), true);
  const invalid = setup();
  invalid.click("invalid");
  assert.equal(invalid.nodes.get("popup-delete-room").classList.contains("show"), false);
  assert.match(invalid.nodes.get("popup-error-message").textContent, /mã phòng/);
});

test("Cancel closes the popup; confirming disables repeat submission", () => {
  const { nodes, click } = setup();
  click();
  nodes.get("delete-room-cancel").emit("click");
  assert.equal(nodes.get("popup-delete-room").classList.contains("show"), false);
  click();
  nodes.get("delete-room-form").emit("submit");
  assert.equal(nodes.get("delete-room-confirm").disabled, true);
});
