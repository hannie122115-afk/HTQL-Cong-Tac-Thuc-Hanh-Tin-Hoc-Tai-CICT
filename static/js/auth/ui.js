/* Dropdown thống nhất, giữ select gốc để submit và các handler change hiện có. */
(() => {
  let current = null;
  const controls = [];
  let nextId = 0;

  function close(restoreFocus = false) {
    if (!current) return;
    const { menu, trigger } = current;
    if (menu.matches(":popover-open")) menu.hidePopover();
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    current = null;
    if (restoreFocus) trigger.focus();
  }

  function enhance(select) {
    if (select.multiple || select.size > 1 || select.classList.contains("ui-native-select")) return;
    const wrapper = document.createElement("div");
    wrapper.className = "ui-select";
    select.before(wrapper);
    wrapper.append(select);
    select.classList.add("ui-native-select");
    select.tabIndex = -1;
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "ui-select-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    const label = document.createElement("span");
    trigger.append(label);
    wrapper.append(trigger);
    const menu = document.createElement("div");
    menu.className = "ui-options";
    menu.id = `ui-options-${++nextId}`;
    menu.setAttribute("role", "listbox");
    menu.setAttribute("popover", "manual");
    menu.hidden = true;
    trigger.setAttribute("aria-controls", menu.id);
    document.body.append(menu);
    const fieldLabel = select.labels?.[0]?.textContent.trim() || select.title || select.name || "Chọn mục";
    trigger.setAttribute("aria-label", fieldLabel);
    menu.setAttribute("aria-label", fieldLabel);
    const control = { select, wrapper, trigger, menu, sync };
    controls.push(control);

    function sync() {
      const text = select.selectedOptions[0]?.textContent.trim() || "Chọn mục";
      if (label.textContent !== text) label.textContent = text;
      trigger.disabled = select.disabled;
      if (wrapper.hidden !== select.hidden) wrapper.hidden = select.hidden;
      trigger.setAttribute("aria-invalid", String(!select.validity.valid));
    }

    function open() {
      close();
      sync();
      if (select.disabled) return;
      menu.replaceChildren();
      const values = new Set();
      for (const option of select.options) {
        if (option.hidden || values.has(option.value)) continue;
        values.add(option.value);
        const item = document.createElement("button");
        item.type = "button";
        item.className = "ui-option";
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", String(option.value === select.value));
        item.textContent = option.textContent.trim();
        item.disabled = option.disabled || option.parentElement.disabled;
        item.addEventListener("click", () => {
          select.value = option.value;
          sync();
          close(true);
          select.dispatchEvent(new Event("input", { bubbles: true }));
          select.dispatchEvent(new Event("change", { bubbles: true }));
        });
        menu.append(item);
      }
      current = control;
      menu.hidden = false;
      if (typeof menu.showPopover === "function") menu.showPopover();
      const rect = trigger.getBoundingClientRect();
      const width = Math.min(Math.max(rect.width, 180), innerWidth - 24);
      menu.style.width = `${width}px`;
      menu.style.left = `${Math.max(12, Math.min(rect.left, innerWidth - width - 12))}px`;
      const below = innerHeight - rect.bottom - 12;
      const above = rect.top - 12;
      const useAbove = below < Math.min(menu.scrollHeight, 260) && above > below;
      const height = Math.min(260, useAbove ? above : below);
      menu.style.maxHeight = `${Math.max(38, height)}px`;
      menu.style.top = `${useAbove ? Math.max(12, rect.top - Math.min(menu.scrollHeight, height) - 6) : rect.bottom + 6}px`;
      trigger.setAttribute("aria-expanded", "true");
      (menu.querySelector('[aria-selected="true"]:not(:disabled)') || menu.querySelector("button:not(:disabled)"))?.focus();
    }

    trigger.addEventListener("click", () => current === control ? close() : open());
    function onKey(event) {
      const items = [...menu.querySelectorAll("button:not(:disabled)")];
      let index = items.indexOf(document.activeElement);
      if (event.key === "Escape") { event.preventDefault(); close(true); return; }
      if (event.key === "Tab") { close(); return; }
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        if (current !== control) { open(); return; }
        index = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1
          : (index + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        items[index]?.focus();
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && event.key !== " ") {
        if (current !== control) open();
        [...menu.querySelectorAll("button:not(:disabled)")].find(item => item.textContent.toLocaleLowerCase().startsWith(event.key.toLocaleLowerCase()))?.focus();
      }
    }
    trigger.addEventListener("keydown", onKey);
    menu.addEventListener("keydown", onKey);
    select.addEventListener("change", sync);
    select.addEventListener("focus", () => trigger.focus());
    select.addEventListener("invalid", event => { event.preventDefault(); sync(); trigger.focus(); });
    select.form?.addEventListener("reset", () => setTimeout(sync, 0));
    new MutationObserver(() => { sync(); if (current === control) close(); })
      .observe(select, { attributes: true, childList: true, subtree: true });
    sync();
  }

  document.querySelectorAll("select").forEach(enhance);
  document.addEventListener("click", event => {
    if (current && !current.wrapper.contains(event.target) && !current.menu.contains(event.target)) close();
  });
  document.addEventListener("focusin", event => {
    if (current && !current.wrapper.contains(event.target) && !current.menu.contains(event.target)) close();
  });
  window.addEventListener("resize", () => close());
  document.addEventListener("scroll", event => {
    if (current && !current.menu.contains(event.target)) close();
  }, true);
  // Đồng bộ giá trị được các form gán bằng JavaScript khi mở popup.
  new MutationObserver(() => controls.forEach(control => control.sync()))
    .observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class", "hidden"] });
})();
