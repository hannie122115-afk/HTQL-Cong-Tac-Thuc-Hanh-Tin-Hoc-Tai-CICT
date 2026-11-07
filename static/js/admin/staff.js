const weeks = JSON.parse(document.getElementById("weeks-data").textContent);
const scheduledRequests = JSON.parse(
  document.getElementById("scheduled-data").textContent,
);
const assignments = JSON.parse(
  document.getElementById("staff-assignments-data").textContent,
);
const pendingAssignments = new Map();

const sessionButtons = document.querySelectorAll(".session-btn");
const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const weekName = document.getElementById("weekName");
const weekSpace = document.getElementById("week-space");
const dayElements = document.querySelectorAll(".day-of-week");
const emptyRow = document.getElementById("empty-schedule-row");
const errorPopup = document.getElementById("popup-error");
const errorMessage = document.getElementById("popup-error-message");
const errorClose = document.getElementById("popup-error-close");
const staffList = document.getElementById("staff-list");
const editButton = document.getElementById("editBtn");
const cancelButton = document.getElementById("cancelBtn");
const saveButton = document.getElementById("saveBtn");
const cancelEditPopup = document.getElementById("popup-cancel-edit");
const cancelEditStayButton = document.getElementById("cancel-edit-stay");
const cancelEditDiscardButton = document.getElementById("cancel-edit-discard");
const successPopup = document.getElementById("popup-success");
const successMessage = document.getElementById("popup-success-message");
let isEditing = false;

function getAssignmentKey(assignment) {
  return [
    assignment.requiredId,
    assignment.roomId,
    assignment.weekId,
    assignment.day,
  ].join(":");
}

function parseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDate(date) {
  return `${String(date.getDate()).padStart(2, "0")}/${String(
    date.getMonth() + 1,
  ).padStart(2, "0")}`;
}

function getDayIndex(dateString) {
  return (parseDate(dateString).getDay() + 6) % 7;
}

// lich co xuat hien trong tuan dang xem k
function getOccurrences(schedule, week) {
  const occurrences = new Set();
  if (schedule.MaTuanHoc !== null && schedule.MaTuanHoc !== undefined) {
    if (Number(schedule.MaTuanHoc) !== Number(week.id)) return occurrences;
    const day = Number(schedule.Thu) - 2;
    if (day >= 0 && day < 7) occurrences.add(day);
    return occurrences;
  }

  const addDate = (date) => {
    if (date && date >= week.start && date <= week.end) {
      occurrences.add(getDayIndex(date));
    }
  };

  addDate(schedule.NgayThucHanh);
  (schedule.DanhSachNgay || "").split(",").filter(Boolean).forEach(addDate);

  if (!schedule.NgayThucHanh && schedule.Thu) {
    const withinRequestWeeks =
      Number(schedule.MaTuanBatDau) <= Number(week.id) &&
      Number(schedule.MaTuanKetThuc) >= Number(week.id);
    const day = Number(schedule.Thu) - 2;
    if (withinRequestWeeks && day >= 0 && day < 7) occurrences.add(day);
  }

  return occurrences;
}

function findCurrentWeek() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return weeks.findIndex((week) => {
    const start = parseDate(week.start);
    const end = parseDate(week.end);
    return today >= start && today <= end;
  });
}

let currentWeekIndex = findCurrentWeek();
if (currentWeekIndex < 0 && weeks.length) currentWeekIndex = 0;

const savedSession = sessionStorage.getItem("staffCalendarSession");
let currentSession = ["1", "2", "3"].includes(savedSession)
  ? savedSession
  : "1";

function showError(message) {
  if (errorPopup && errorMessage) {
    errorMessage.textContent = message;
    errorPopup.classList.add("show");
  } else {
    window.alert(message);
  }
}

errorClose?.addEventListener("click", () => {
  errorPopup.classList.remove("show");
});

function renderWeek() {
  if (currentWeekIndex < 0 || !weeks.length) {
    weekName.textContent = "Chưa có dữ liệu tuần học";
    weekSpace.textContent = "";
    previousWeek.disabled = true;
    nextWeek.disabled = true;
    dayElements.forEach((element) => {
      element.textContent = "";
    });
    return;
  }

  const week = weeks[currentWeekIndex];
  weekName.textContent = `Tuần ${week.name}`;
  weekSpace.textContent = `${formatDate(parseDate(week.start))} - ${formatDate(
    parseDate(week.end),
  )}`;

  dayElements.forEach((element) => {
    const date = parseDate(week.start);
    date.setDate(date.getDate() + Number(element.dataset.day));
    element.textContent = `(${formatDate(date)})`;
  });

  previousWeek.disabled = currentWeekIndex === 0;
  nextWeek.disabled = currentWeekIndex === weeks.length - 1;
}

function renderCalendar() {
  document.querySelectorAll(".schedule-cell").forEach((cell) => {
    cell.replaceChildren();
    cell.classList.remove("staff-scheduled-slot");
    delete cell.dataset.requiredId;
    delete cell.dataset.weekId;
    delete cell.dataset.staffId;
  });

  document.querySelectorAll(".staff-room-row").forEach((row) => {
    row.hidden = true;
  });

  if (emptyRow) emptyRow.hidden = true;
  if (currentWeekIndex < 0 || !weeks.length) {
    if (emptyRow) emptyRow.hidden = false;
    return;
  }

  const week = weeks[currentWeekIndex];
  const occupiedCells = new Set();

  scheduledRequests.forEach((schedule) => {
    if (Number(schedule.BuoiThucHanh) !== Number(currentSession)) return;

    getOccurrences(schedule, week).forEach((day) => {
      const cell = document.querySelector(
        `.schedule-cell[data-room="${schedule.MaPhong}"][data-day="${day}"]`,
      );
      if (!cell) return;

      const row = cell.closest(".staff-room-row");
      if (row) row.hidden = false;

      cell.classList.add("staff-scheduled-slot");
      if (!cell.dataset.requiredId) {
        cell.dataset.requiredId = String(schedule.MaYeuCau);
        cell.dataset.weekId = String(week.id);

        const assigned = assignments.find(
          (item) =>
            String(item.MaYeuCau) === String(schedule.MaYeuCau) &&
            String(item.MaPhong) === String(schedule.MaPhong) &&
            Number(item.MaTuanHoc) === Number(week.id) &&
            Number(item.Thu) === day + 2,
        );
        const pending = pendingAssignments.get(
          getAssignmentKey({
            requiredId: schedule.MaYeuCau,
            roomId: schedule.MaPhong,
            weekId: week.id,
            day,
          }),
        );
        const displayedAssignment = pending
          ? pending.staffId
            ? pending
            : null
          : assigned && {
              staffId: assigned.MaCanBo,
              staffName: assigned.TenCanBo,
            };
        if (displayedAssignment) {
          cell.dataset.staffId = String(displayedAssignment.staffId);
          const staffCard = document.createElement("div");
          staffCard.className = "staff-assigned-name";
          staffCard.textContent = displayedAssignment.staffName;
          staffCard.draggable = isEditing;
          staffCard.dataset.assignmentKey = getAssignmentKey({
            requiredId: schedule.MaYeuCau,
            roomId: schedule.MaPhong,
            weekId: week.id,
            day,
          });
          staffCard.addEventListener("dragstart", (event) => {
            if (!isEditing) {
              event.preventDefault();
              return;
            }
            event.dataTransfer.setData(
              "application/x-staff-assignment",
              JSON.stringify({
                requiredId: Number(schedule.MaYeuCau),
                roomId: Number(schedule.MaPhong),
                weekId: Number(week.id),
                day,
                session: Number(schedule.BuoiThucHanh),
                staffId: Number(displayedAssignment.staffId),
                staffName: displayedAssignment.staffName,
              }),
            );
            event.dataTransfer.effectAllowed = "move";
            staffCard.classList.add("dragging");
          });
          staffCard.addEventListener("dragend", () => {
            staffCard.classList.remove("dragging");
          });
          cell.appendChild(staffCard);
        } else {
          delete cell.dataset.staffId;
        }
      }

      occupiedCells.add(cell);
    });
  });

  if (emptyRow) emptyRow.hidden = occupiedCells.size > 0;
  updateSaveButton();
}

function updateSaveButton() {
  if (!saveButton) return;
  saveButton.innerHTML =
    `<i class="fa-solid fa-floppy-disk"></i> Lưu` +
    (pendingAssignments.size ? ` (${pendingAssignments.size})` : "");
}

function setEditingMode(editing) {
  isEditing = editing;
  staffList.classList.toggle("is-locked", !editing);
  staffList.setAttribute("aria-disabled", String(!editing));
  staffList.querySelectorAll(".staff-item").forEach((item) => {
    item.draggable = editing;
  });
  document.querySelectorAll(".staff-assigned-name").forEach((item) => {
    item.draggable = editing;
  });

  editButton.hidden = editing;
  cancelButton.hidden = !editing;
  saveButton.hidden = !editing;
}

function selectSession(session) {
  currentSession = session;
  sessionStorage.setItem("staffCalendarSession", session);
  sessionButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.session === session);
  });
  renderCalendar();
}

document.querySelectorAll(".staff-item").forEach((item) => {
  item.addEventListener("dragstart", (event) => {
    if (!isEditing) {
      event.preventDefault();
      return;
    }
    event.dataTransfer.setData("text/plain", item.dataset.staffId);
    event.dataTransfer.effectAllowed = "copy";
    item.classList.add("dragging");
  });

  item.addEventListener("dragend", () => {
    item.classList.remove("dragging");
  });
});

document.querySelectorAll(".schedule-cell").forEach((cell) => {
  cell.addEventListener("dragover", (event) => {
    if (!isEditing || !cell.classList.contains("staff-scheduled-slot")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    cell.classList.add("staff-drag-over");
  });

  cell.addEventListener("dragleave", () => {
    cell.classList.remove("staff-drag-over");
  });

  cell.addEventListener("drop", (event) => {
    event.preventDefault();
    cell.classList.remove("staff-drag-over");
    if (!isEditing || !cell.classList.contains("staff-scheduled-slot")) return;

    const assignedStaffData = event.dataTransfer.getData(
      "application/x-staff-assignment",
    );
    if (assignedStaffData) return;

    const staffId = event.dataTransfer.getData("text/plain");
    if (!staffId) return;

    const staffItem = document.querySelector(
      `.staff-item[data-staff-id="${CSS.escape(staffId)}"]`,
    );
    if (!staffItem) return;

    const assignment = {
      requiredId: Number(cell.dataset.requiredId),
      roomId: Number(cell.dataset.room),
      weekId: Number(cell.dataset.weekId),
      day: Number(cell.dataset.day),
      session: Number(currentSession),
      staffId: Number(staffId),
      staffName: staffItem.textContent.trim(),
    };
    pendingAssignments.set(getAssignmentKey(assignment), assignment);
    renderCalendar();
  });
});

staffList.addEventListener("dragover", (event) => {
  if (!isEditing) return;
  if (!event.dataTransfer.types.includes("application/x-staff-assignment")) {
    return;
  }
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  staffList.classList.add("staff-drop-target");
});

staffList.addEventListener("dragleave", (event) => {
  if (!staffList.contains(event.relatedTarget)) {
    staffList.classList.remove("staff-drop-target");
  }
});

staffList.addEventListener("drop", (event) => {
  event.preventDefault();
  staffList.classList.remove("staff-drop-target");
  if (!isEditing) return;

  const assignmentData = event.dataTransfer.getData(
    "application/x-staff-assignment",
  );
  if (!assignmentData) return;

  const assignment = JSON.parse(assignmentData);
  const key = getAssignmentKey(assignment);
  const savedAssignment = assignments.find(
    (item) =>
      Number(item.MaYeuCau) === assignment.requiredId &&
      Number(item.MaPhong) === assignment.roomId &&
      Number(item.MaTuanHoc) === assignment.weekId &&
      Number(item.Thu) === assignment.day + 2,
  );

  if (savedAssignment) {
    pendingAssignments.set(key, {
      ...assignment,
      staffId: null,
      staffName: "",
    });
  } else {
    pendingAssignments.delete(key);
  }
  renderCalendar();
});

editButton.addEventListener("click", () => {
  setEditingMode(true);
});

saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  if (!pendingAssignments.size) {
    setEditingMode(false);
    saveButton.disabled = false;
    return;
  }

  saveButton.textContent = "Đang lưu...";
  const failures = [];

  for (const [key, assignment] of pendingAssignments) {
    try {
      const response = await fetch("/admin/staff/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(assignment),
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.message || "Không thể lưu phân công.");
      }

      pendingAssignments.delete(key);
      const savedIndex = assignments.findIndex(
        (item) =>
          Number(item.MaYeuCau) === assignment.requiredId &&
          Number(item.MaPhong) === assignment.roomId &&
          Number(item.MaTuanHoc) === assignment.weekId &&
          Number(item.Thu) === assignment.day + 2,
      );
      if (assignment.staffId === null) {
        if (savedIndex >= 0) assignments.splice(savedIndex, 1);
      } else if (savedIndex >= 0) {
        assignments[savedIndex].MaCanBo = result.staffId;
        assignments[savedIndex].TenCanBo = result.staffName;
      } else {
        assignments.push({
          MaYeuCau: assignment.requiredId,
          MaPhong: assignment.roomId,
          MaTuanHoc: assignment.weekId,
          Thu: assignment.day + 2,
          MaCanBo: result.staffId,
          TenCanBo: result.staffName,
        });
      }
    } catch (error) {
      failures.push(error.message || "Không thể lưu phân công.");
    }
  }

  renderCalendar();
  if (failures.length) {
    showError(failures.join("\n"));
  } else {
    setEditingMode(false);
    if (successPopup && successMessage) {
      successMessage.textContent = "Phân công cán bộ thành công!";
      successPopup.classList.add("show");
      setTimeout(() => {
        window.location.reload();
      }, 300);
    }
  }
  saveButton.disabled = false;
  updateSaveButton();
});

cancelButton.addEventListener("click", () => {
  cancelEditPopup.classList.add("show");
});

cancelEditStayButton.addEventListener("click", () => {
  cancelEditPopup.classList.remove("show");
});

cancelEditDiscardButton.addEventListener("click", () => {
  pendingAssignments.clear();
  cancelEditPopup.classList.remove("show");
  setEditingMode(false);
  renderCalendar();
});

previousWeek.addEventListener("click", () => {
  if (currentWeekIndex > 0) {
    currentWeekIndex -= 1;
    renderWeek();
    renderCalendar();
  }
});

nextWeek.addEventListener("click", () => {
  if (currentWeekIndex < weeks.length - 1) {
    currentWeekIndex += 1;
    renderWeek();
    renderCalendar();
  }
});

sessionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    selectSession(button.dataset.session);
  });
});

renderWeek();
selectSession(currentSession);
setEditingMode(false);
