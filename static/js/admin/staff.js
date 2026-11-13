(() => {
  const form = document.getElementById("staff-assignment-form");
  if (!form) return;
  const canAssign = form.dataset.canAssign === "true";
  const staffItems = [...document.querySelectorAll(".staff-item")];
  const rooms = [...document.querySelectorAll(".assignment-room")];
  const staffNames = new Map(
    staffItems.map((item) => [item.dataset.staffId, item.dataset.staffName]),
  );
  let saved = new Map(
    rooms.map((room) => [room.dataset.roomId, room.dataset.staffId || ""]),
  );
  let selectedStaff = "";
  let draggedStaff = "";
  let saving = false;
  const saveButton = document.getElementById("saveBtn");
  const resetButton = document.getElementById("resetBtn");
  const status = document.getElementById("assignment-status");
  const errorPopup = document.getElementById("popup-error");
  document
    .getElementById("popup-error-close")
    ?.addEventListener("click", () => errorPopup.classList.remove("show"));

  function changes() {
    return rooms.filter(
      (room) => (room.dataset.staffId || "") !== saved.get(room.dataset.roomId),
    );
  }

  function render() {
    const counts = new Map();
    rooms.forEach((room) => {
      const id = room.dataset.staffId;
      const assigned = staffNames.has(id);
      room.classList.toggle("is-assigned", assigned);
      room.querySelector(".room-state-icon").className =
        "room-state-icon fa-solid " +
        (assigned ? "fa-circle-check" : "fa-plus");
      room.querySelector(".room-assignee").hidden = !assigned;
      room.querySelector(".room-staff-name").textContent = assigned
        ? staffNames.get(id)
        : "";
      room.querySelector(".room-select").disabled = !canAssign || saving;
      room.querySelector(".remove-assignment").disabled = !canAssign || saving;
      if (assigned) counts.set(id, (counts.get(id) || 0) + 1);
    });
    staffItems.forEach((item) => {
      item.querySelector(".staff-room-count").textContent =
        "Số phòng được phân công: " + (counts.get(item.dataset.staffId) || 0);
      item.classList.toggle(
        "is-selected",
        item.dataset.staffId === selectedStaff,
      );
      item.setAttribute(
        "aria-pressed",
        String(item.dataset.staffId === selectedStaff),
      );
      item.disabled = !canAssign || saving;
      item.draggable = canAssign && !saving;
    });
    if (saveButton) saveButton.disabled = saving || !changes().length;
    if (resetButton) resetButton.disabled = saving || !changes().length;
  }

  function assign(room, id) {
    if (!canAssign || saving || !staffNames.has(id)) return;
    room.dataset.staffId = id;
    status.textContent =
      "Đã phân công " + staffNames.get(id) + ". Bấm Lưu thay đổi để lưu.";
    render();
  }

  staffItems.forEach((item) => {
    item.addEventListener("click", () => {
      if (!canAssign || saving) return;
      selectedStaff =
        selectedStaff === item.dataset.staffId ? "" : item.dataset.staffId;
      status.textContent = selectedStaff
        ? "Đã chọn " +
          staffNames.get(selectedStaff) +
          ". Chọn phòng để phân công."
        : "";
      render();
    });
    item.addEventListener("dragstart", (event) => {
      if (!canAssign || saving) {
        event.preventDefault();
        return;
      }
      draggedStaff = item.dataset.staffId;
      event.dataTransfer.setData("text/plain", draggedStaff);
      event.dataTransfer.effectAllowed = "copy";
      item.classList.add("dragging");
    });
    item.addEventListener("dragend", () => {
      draggedStaff = "";
      item.classList.remove("dragging");
      rooms.forEach((room) => room.classList.remove("is-drag-over"));
    });
  });

  rooms.forEach((room) => {
    room.addEventListener("dragover", (event) => {
      if (!canAssign || saving || !staffNames.has(draggedStaff)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      room.classList.add("is-drag-over");
    });
    room.addEventListener("dragleave", (event) => {
      if (!room.contains(event.relatedTarget))
        room.classList.remove("is-drag-over");
    });
    room.addEventListener("drop", (event) => {
      event.preventDefault();
      room.classList.remove("is-drag-over");
      if (draggedStaff) assign(room, event.dataTransfer.getData("text/plain"));
    });
    room.querySelector(".room-select").addEventListener("click", () => {
      if (selectedStaff) assign(room, selectedStaff);
      else status.textContent = "Hãy chọn một cán bộ từ danh sách trước.";
    });
    room.querySelector(".remove-assignment").addEventListener("click", () => {
      if (!canAssign || saving) return;
      room.dataset.staffId = "";
      status.textContent = "Đã bỏ phân công. Bấm Lưu thay đổi để lưu.";
      render();
    });
  });

  resetButton?.addEventListener("click", () => {
    if (saving) return;
    rooms.forEach((room) => {
      room.dataset.staffId = saved.get(room.dataset.roomId);
    });
    selectedStaff = "";
    status.textContent = "Đã khôi phục phân công đã lưu.";
    render();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!canAssign || saving || !changes().length) return;
    const assignments = changes().map((room) => ({
      roomId: Number(room.dataset.roomId),
      staffId: room.dataset.staffId ? Number(room.dataset.staffId) : null,
    }));
    saving = true;
    status.textContent = "Đang lưu phân công...";
    render();
    try {
      const response = await fetch("/admin/staff/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assignments }),
      });
      const result = await response.json().catch(() => ({
        success: false,
        message: "Không thể lưu phân công. Vui lòng thử lại.",
      }));
      if (!response.ok || !result.success)
        throw new Error(result.message || "Không thể lưu phân công.");
      saved = new Map(
        rooms.map((room) => [room.dataset.roomId, room.dataset.staffId || ""]),
      );
      status.textContent = "Lưu phân công cán bộ thành công!";
    } catch (error) {
      status.textContent = "Chưa lưu được thay đổi. Vui lòng thử lại.";
      document.getElementById("popup-error-message").textContent =
        error.message || "Không thể lưu phân công.";
      errorPopup.classList.add("show");
    } finally {
      saving = false;
      render();
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (!changes().length) return;
    event.preventDefault();
    event.returnValue = "";
  });
  render();
})();
