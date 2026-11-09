/* Lịch chọn ngày chung; input date gốc vẫn lưu giá trị và tham gia submit. */
(() => {
  let opened = null;
  let sequence = 0;
  const controls = [];
  const iso = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const parse = value => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    return iso(date) === value ? date : null;
  };

  function close(focus = false) {
    if (!opened) return;
    const control = opened;
    opened = null;
    if (control.panel.matches(":popover-open")) control.panel.hidePopover();
    control.panel.hidden = true;
    control.trigger.setAttribute("aria-expanded", "false");
    if (focus) control.trigger.focus();
  }

  document.querySelectorAll('input[type="date"]').forEach(input => {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-date";
    input.before(wrapper);
    wrapper.append(input);
    input.classList.add("ui-native-date");
    input.tabIndex = -1;
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "ui-date-trigger";
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-label", input.labels?.[0]?.textContent.trim() || input.title || "Chọn ngày");
    const value = document.createElement("span");
    trigger.append(value);
    wrapper.append(trigger);
    const panel = document.createElement("div");
    panel.className = "ui-date-popover";
    panel.id = `date-picker-${++sequence}`;
    panel.setAttribute("popover", "manual");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Chọn ngày");
    panel.hidden = true;
    trigger.setAttribute("aria-controls", panel.id);
    document.body.append(panel);
    let month;
    let focused;
    const allowed = date => (!input.min || iso(date) >= input.min) && (!input.max || iso(date) <= input.max);
    const clamp = date => input.min && iso(date) < input.min ? parse(input.min) : input.max && iso(date) > input.max ? parse(input.max) : date;
    function sync() {
      const date = parse(input.value);
      const label = date ? date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }) : "dd/mm/yyyy";
      if (value.textContent !== label) value.textContent = label;
      trigger.disabled = input.disabled || input.readOnly;
      if (wrapper.hidden !== input.hidden) wrapper.hidden = input.hidden;
    }
    const control = { panel, trigger, wrapper, sync };
    controls.push(control);

    function choose(date) {
      input.value = date ? iso(date) : "";
      trigger.removeAttribute("aria-invalid");
      sync();
      close(true);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    function button(text, className, action) {
      const el = document.createElement("button");
      el.type = "button";
      el.className = className;
      el.textContent = text;
      el.addEventListener("click", action);
      return el;
    }
    function render() {
      panel.replaceChildren();
      const header = document.createElement("div");
      header.className = "ui-date-header";
      const previous = button("‹", "ui-date-nav", () => moveMonth(-1));
      previous.setAttribute("aria-label", "Tháng trước");
      previous.disabled = !!input.min && iso(new Date(month.getFullYear(), month.getMonth(), 0)) < input.min;
      const caption = document.createElement("div");
      caption.className = "ui-date-caption";
      const monthLabel = document.createElement("strong");
      monthLabel.textContent = `Tháng ${month.getMonth() + 1}`;
      const yearInput = document.createElement("input");
      yearInput.type = "number";
      yearInput.className = "ui-date-year";
      yearInput.min = "100";
      yearInput.max = "9999";
      yearInput.value = String(month.getFullYear());
      yearInput.setAttribute("aria-label", "Năm — nhập để chuyển nhanh");
      yearInput.addEventListener("change", () => {
        const year = Number(yearInput.value);
        if (!Number.isInteger(year) || year < 100 || year > 9999) {
          yearInput.value = String(month.getFullYear());
          return;
        }
        focused = clamp(new Date(year, month.getMonth(), 1));
        month = new Date(focused.getFullYear(), focused.getMonth(), 1);
        render();
        focusDay();
      });
      caption.append(monthLabel, yearInput);
      const next = button("›", "ui-date-nav", () => moveMonth(1));
      next.setAttribute("aria-label", "Tháng sau");
      next.disabled = !!input.max && iso(new Date(month.getFullYear(), month.getMonth() + 1, 1)) > input.max;
      header.append(previous, caption, next);
      panel.append(header);
      const grid = document.createElement("div");
      grid.className = "ui-date-grid";
      for (const name of ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]) {
        const weekday = document.createElement("span");
        weekday.className = "ui-date-weekday";
        weekday.textContent = name;
        grid.append(weekday);
      }
      const first = new Date(month.getFullYear(), month.getMonth(), 1);
      const offset = (first.getDay() + 6) % 7;
      const today = iso(new Date());
      for (let i = 0; i < 42; i++) {
        const date = new Date(month.getFullYear(), month.getMonth(), i - offset + 1);
        const day = button(String(date.getDate()), "ui-date-day", () => choose(date));
        day.dataset.date = iso(date);
        day.setAttribute("aria-label", date.toLocaleDateString("vi-VN", { weekday: "long", day: "numeric", month: "long", year: "numeric" }));
        day.disabled = !allowed(date);
        day.tabIndex = iso(date) === iso(focused) ? 0 : -1;
        if (date.getMonth() !== month.getMonth()) day.classList.add("is-outside");
        if (iso(date) === today) { day.classList.add("is-today"); day.setAttribute("aria-current", "date"); }
        if (iso(date) === input.value) { day.classList.add("is-selected"); day.setAttribute("aria-pressed", "true"); }
        grid.append(day);
      }
      panel.append(grid);
      const footer = document.createElement("div");
      footer.className = "ui-date-footer";
      const clear = button("Xóa ngày", "ui-date-action", () => choose(null));
      clear.disabled = input.required;
      const todayButton = button("Hôm nay", "ui-date-action", () => choose(new Date()));
      todayButton.disabled = !allowed(new Date());
      footer.append(clear, todayButton);
      panel.append(footer);
    }
    function focusDay() {
      panel.querySelector(`[data-date="${iso(focused)}"]:not(:disabled)`)?.focus();
    }
    function moveMonth(delta) {
      focused = clamp(new Date(month.getFullYear(), month.getMonth() + delta, 1));
      month = new Date(focused.getFullYear(), focused.getMonth(), 1);
      render();
      focusDay();
    }
    function open() {
      close();
      sync();
      if (trigger.disabled) return;
      focused = clamp(parse(input.value) || new Date());
      month = new Date(focused.getFullYear(), focused.getMonth(), 1);
      render();
      panel.hidden = false;
      if (typeof panel.showPopover === "function") panel.showPopover();
      const rect = trigger.getBoundingClientRect();
      const width = Math.min(310, innerWidth - 24);
      panel.style.width = `${width}px`;
      panel.style.left = `${Math.max(12, Math.min(rect.left, innerWidth - width - 12))}px`;
      const height = panel.getBoundingClientRect().height;
      panel.style.top = `${Math.max(12, Math.min(rect.bottom + 6, innerHeight - height - 12))}px`;
      opened = control;
      trigger.setAttribute("aria-expanded", "true");
      focusDay();
    }
    trigger.addEventListener("click", () => opened === control ? close() : open());
    trigger.addEventListener("keydown", event => {
      if (event.key === "ArrowDown") { event.preventDefault(); open(); }
    });
    panel.addEventListener("keydown", event => {
      if (event.key === "Escape") { event.preventDefault(); close(true); return; }
      if (!event.target.matches(".ui-date-day")) return;
      const date = parse(event.target.dataset.date);
      const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
      if (delta === undefined && !["Home", "End", "PageUp", "PageDown"].includes(event.key)) return;
      event.preventDefault();
      if (delta !== undefined) date.setDate(date.getDate() + delta);
      else if (event.key === "Home") date.setDate(date.getDate() - (date.getDay() + 6) % 7);
      else if (event.key === "End") date.setDate(date.getDate() + 6 - (date.getDay() + 6) % 7);
      else { moveMonth(event.key === "PageUp" ? -1 : 1); return; }
      focused = clamp(date);
      month = new Date(focused.getFullYear(), focused.getMonth(), 1);
      render();
      focusDay();
    });
    input.addEventListener("change", sync);
    input.addEventListener("focus", () => trigger.focus());
    input.addEventListener("invalid", event => { event.preventDefault(); trigger.setAttribute("aria-invalid", "true"); trigger.focus(); });
    input.form?.addEventListener("reset", () => setTimeout(sync, 0));
    new MutationObserver(sync).observe(input, { attributes: true });
    sync();
  });
  document.addEventListener("click", event => {
    // Giữ đường đi ban đầu của click: render() có thể đã tháo nút chuyển tháng khỏi DOM.
    const path = event.composedPath();
    if (opened && !path.includes(opened.wrapper) && !path.includes(opened.panel)) close();
  });
  document.addEventListener("focusin", event => {
    if (opened && !opened.wrapper.contains(event.target) && !opened.panel.contains(event.target)) close();
  });
  document.addEventListener("scroll", event => { if (opened && !opened.panel.contains(event.target)) close(); }, true);
  window.addEventListener("resize", () => close());
  new MutationObserver(() => controls.forEach(control => control.sync()))
    .observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class", "hidden"] });
})();
