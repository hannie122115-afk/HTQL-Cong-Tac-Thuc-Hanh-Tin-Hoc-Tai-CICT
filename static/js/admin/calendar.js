const weeks = JSON.parse(document.getElementById("weeks-data").textContent);
const scheduledRequests = JSON.parse(
  document.getElementById("scheduled-data").textContent,
);

let temporarySchedules = [];
let isEditing = false;

let removedScheduleDays = new Set(); // lưu các thứ trong 1 yêu cầu
function getScheduleDayKey(requiredId, day) {
  return `${String(requiredId)}:${Number(day)}`;
}

let removedScheduleDayWeeks = new Set(); //lưu cho trường hợp xóa 1 yêu cầu dài hạn nhưng chỉ xóa của 1 tuần
function getScheduleDayWeekKey(requiredId, day, weekId) {
  return `${getScheduleDayKey(requiredId, day)}:${Number(weekId)}`;
}

function clearRemovedScheduleDay(requiredId, day) {
  const dayKey = getScheduleDayKey(requiredId, day);

  removedScheduleDays.delete(dayKey);
  removedScheduleDayWeeks.forEach((key) => {
    if (key.startsWith(`${dayKey}:`)) {
      removedScheduleDayWeeks.delete(key);
    }
  });
}

const today = new Date();

function getMonday(date) {
  const monday = new Date(date);
  const day = monday.getDay();

  monday.setDate(monday.getDate() - (day === 0 ? 6 : day - 1));
  monday.setHours(0, 0, 0, 0);

  return monday;
}

let currentMonday = getMonday(today);

function formatDate(date) {
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");

  return `${day}/${month}`;
}

function parseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toDateString(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

// ================= LẤY DANH SÁCH LỊCH =================

function getAllSchedules() {
  const databaseSchedules = scheduledRequests.map((item) => ({
    source: "database",
    requiredId: String(item.MaYeuCau),
    roomId: Number(item.MaPhong),
    session: Number(item.BuoiThucHanh),
    date: item.NgayThucHanh || "",
    days: item.DanhSachThu || "",
    dates: (item.DanhSachNgay || "").split(",").filter(Boolean),
    weekStart: Number(item.MaTuanBatDau),
    weekEnd: Number(item.MaTuanKetThuc),
    currentWeekOnly: false,
  }));

  const newSchedules = temporarySchedules.map((item) => ({
    source: "temporary",
    requiredId: String(item.requiredId),
    roomId: Number(item.roomId),
    session: Number(item.session),
    date: item.date || "",
    days: item.days || "",
    dates: [],
    weekStart: Number(item.weekStart),
    weekEnd: Number(item.weekEnd),
    weekId: Number(item.weekId),
    day: Number(item.day),
    currentWeekOnly: Boolean(item.currentWeekOnly),
  }));

  return [...databaseSchedules, ...newSchedules];
}

// ================= VẼ LỊCH =================

let currentIndex = -1;
let currentSession = "1";
function renderScheduledRequests() {
  // Xóa lịch đang hiển thị trước khi vẽ lại
  document.querySelectorAll(".schedule-cell").forEach((cell) => {
    cell.innerHTML = "";
    delete cell.dataset.occupied;
    delete cell.dataset.requiredId;
  });

  if (currentIndex < 0 || !weeks.length) return;

  const currentWeek = weeks[currentIndex];
  const allSchedules = getAllSchedules();

  allSchedules.forEach((schedule) => {
    let occurrences = [];
    const databaseItem =
      schedule.source === "database"
        ? scheduledRequests.find(
            (item) => String(item.MaYeuCau) === schedule.requiredId,
          )
        : null;

    const temporaryItem =
      schedule.source === "temporary"
        ? temporarySchedules.find(
            (item) => String(item.requiredId) === schedule.requiredId,
          )
        : null;

    const item = databaseItem || temporaryItem;

    if (!item) return;

    // co hien thi dung tuan k
    if (schedule.date) {
      if (
        schedule.date < currentWeek.start ||
        schedule.date > currentWeek.end
      ) {
        return;
      }
    } else {
      if (schedule.currentWeekOnly && schedule.weekId !== currentWeek.id) {
        return;
      }
      if (
        !schedule.currentWeekOnly &&
        (schedule.weekStart > currentWeek.id ||
          schedule.weekEnd < currentWeek.id)
      ) {
        return;
      }
    }

    if (schedule.date) {
      occurrences.push({
        date: schedule.date,
        day: (parseDate(schedule.date).getDay() + 6) % 7,
      });
    } else if (schedule.source === "temporary") {
      const date = new Date(parseDate(currentWeek.start));
      date.setDate(date.getDate() + schedule.day);
      occurrences.push({
        date: schedule.currentWeekOnly ? toDateString(date) : "",
        day: schedule.day,
      });
    } else {
      const recurringDays = schedule.days
        .split(",")
        .filter(Boolean)
        .map((day) => Number(day.trim()) - 2);
      recurringDays.forEach((day) => occurrences.push({ date: "", day }));
      schedule.dates.forEach((date) => {
        const scheduledDate = parseDate(date);
        if (date >= currentWeek.start && date <= currentWeek.end) {
          occurrences.push({
            date,
            day: (scheduledDate.getDay() + 6) % 7,
          });
        }
      });
    }

    occurrences = occurrences.filter(
      ({ day, date }) =>
        day >= 0 &&
        day <= 6 &&
        !removedScheduleDays.has(getScheduleDayKey(schedule.requiredId, day)) &&
        !removedScheduleDayWeeks.has(
          getScheduleDayWeekKey(schedule.requiredId, day, currentWeek.id),
        ) &&
        (!date || (date >= currentWeek.start && date <= currentWeek.end)),
    );

    occurrences.forEach(({ day, date }) => {
      if (day < 0 || day > 6) return;

      const cell = document.querySelector(
        `.schedule-cell[data-room="${schedule.roomId}"][data-day="${day}"]`,
      );

      if (!cell) return;

      if (schedule.session !== Number(currentSession)) return;

      const card = document.createElement("div");
      card.className = "scheduled-item";
      card.draggable = isEditing;
      card.dataset.day = String(day);

      const course = item.TenHocPhan || item.course || "";
      const teacher = item.TenGiangVien || item.teacher || "";

      card.textContent = `${course} - ${teacher}`;

      card.dataset.requiredId = schedule.requiredId;
      card.dataset.course = course;
      card.dataset.teacher = teacher;
      card.dataset.session = schedule.session;
      card.dataset.machines = item.SoLuongMay || item.machines || "";
      card.dataset.software = item.MaPhanMem || item.software || "";
      card.dataset.date = date;
      card.dataset.days = schedule.days;
      card.dataset.weekStart = schedule.weekStart || "";
      card.dataset.weekEnd = schedule.weekEnd || "";
      card.dataset.weekStartName = item.TuanBatDau || item.weekStartName || "";
      card.dataset.weekEndName = item.TuanKetThuc || item.weekEndName || "";

      if (temporaryItem) {
        card.requiredItem = temporaryItem.requiredItem || null;
      }

      cell.appendChild(card);
      cell.dataset.occupied = "true";
      cell.dataset.requiredId = schedule.requiredId;
    });
  });
}

// ================= HIỂN THỊ TUẦN =================

const dayElements = document.querySelectorAll(".day-of-week");
const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const weekName = document.getElementById("weekName");
const weekSpace = document.getElementById("week-space");

function renderCalendarWeek() {
  if (weeks.length === 0 || currentIndex < 0) {
    weekName.textContent = "Chưa có dữ liệu tuần học";
    previousWeek.disabled = true;
    nextWeek.disabled = true;

    dayElements.forEach((element) => {
      element.textContent = "";
    });

    return;
  }

  const week = weeks[currentIndex];

  weekName.textContent = week.name;
  weekSpace.textContent = `${formatDate(parseDate(week.start))} - ${formatDate(parseDate(week.end))}`;

  dayElements.forEach((element) => {
    const dayIndex = Number(element.dataset.day);
    const date = parseDate(week.start);

    date.setDate(date.getDate() + dayIndex);

    element.textContent = `(${formatDate(date)})`;
  });

  previousWeek.disabled = currentIndex === 0;
  nextWeek.disabled = currentIndex === weeks.length - 1;
}

// ================= CHUYỂN TUẦN =================

previousWeek.addEventListener("click", () => {
  if (currentIndex > 0) {
    currentIndex--;
    renderCalendarWeek();
    renderScheduledRequests();
  }
});

nextWeek.addEventListener("click", () => {
  if (currentIndex < weeks.length - 1) {
    currentIndex++;
    renderCalendarWeek();
    renderScheduledRequests();
  }
});

function findCurrentWeek() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);

  return weeks.findIndex((week) => {
    const start = parseDate(week.start);
    const end = parseDate(week.end);

    return now >= start && now <= end;
  });
}

function findCurrentWeek() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);

  return weeks.findIndex((week) => {
    const start = parseDate(week.start);
    const end = parseDate(week.end);

    return now >= start && now <= end;
  });
}

currentIndex = findCurrentWeek();

if (currentIndex === -1 && weeks.length > 0) {
  currentIndex = 0;
}

// ================= CHỌN BUỔI =================

const sessionBtn = document.querySelectorAll(".session-btn");
const calendarBody = document.getElementById("calendar-body");

function changeSession(session) {
  currentSession = session;

  sessionBtn.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.session === session);
  });

  renderScheduledRequests();
}

sessionBtn.forEach((btn) => {
  btn.addEventListener("click", () => {
    changeSession(btn.dataset.session);
  });
});

changeSession("1");
renderCalendarWeek();

// ================= POPUP =================

const popupError = document.getElementById("popup-error");
const popupMessageError = document.getElementById("popup-error-message");
const popupErrorClose = document.getElementById("popup-error-close");

function showErrorPopup(message) {
  if (popupMessageError && popupError) {
    popupMessageError.textContent = message;
    popupError.classList.add("show");
  } else {
    window.alert(message);
  }
}

popupErrorClose?.addEventListener("click", () => {
  popupError.classList.remove("show");
});

const popupSuccess = document.getElementById("popup-success");
const popupSuccessMessage = document.getElementById("popup-success-message");
const popupSuccessClose = document.getElementById("popup-success-close");
const calendarPage = document.getElementById("accept-page");

if (calendarPage?.dataset.success) {
  popupSuccessMessage.textContent = calendarPage.dataset.success;
  popupSuccess.classList.add("show");
}

popupSuccessClose?.addEventListener("click", () => {
  popupSuccess.classList.remove("show");
});

// ================= KIỂM TRA NGÀY YÊU CẦU =================

function checkRequestDate(item, day, weekId, targetDate) {
  if (item.dataset.date) {
    return item.dataset.date === targetDate;
  }

  const startWeek = Number(item.dataset.weekStart);
  const endWeek = Number(item.dataset.weekEnd);

  if (weekId < startWeek || weekId > endWeek) {
    return false;
  }

  const requiredDays = (item.dataset.days || "")
    .split(",")
    .filter(Boolean)
    .map((d) => Number(d.trim()) - 2);

  return requiredDays.includes(day);
}

// ================= KIỂM TRA PHÒNG =================

function checkRoomSuitableJS(room, item) {
  const roomStatus = Number(room.dataset.roomStatus);
  const machineCount = Number(room.dataset.machineCount);
  const configId = room.dataset.configId;

  const softwareList = JSON.parse(room.dataset.software || "[]");

  if (roomStatus !== 1) return false;
  if (!configId) return false;

  if (machineCount < Number(item.dataset.machines)) {
    return false;
  }

  if (!softwareList.includes(Number(item.dataset.software))) {
    return false;
  }

  return true;
}

// ================= KIỂM TRA XUNG ĐỘT =================

let draggedItem = null;

function checkConflictJS(roomId, session, day, weekId, targetDate) {
  const allSchedules = getAllSchedules();

  for (const item of allSchedules) {
    if (
      draggedItem &&
      String(item.requiredId) === String(draggedItem.dataset.requiredId)
    ) {
      continue;
    }

    if (
      Number(item.roomId) !== Number(roomId) ||
      Number(item.session) !== Number(session)
    ) {
      continue;
    }

    if (
      removedScheduleDays.has(getScheduleDayKey(item.requiredId, day)) ||
      removedScheduleDayWeeks.has(
        getScheduleDayWeekKey(item.requiredId, day, weekId),
      )
    ) {
      continue;
    }

    if (item.date) {
      if (item.date === targetDate) {
        return true;
      }
      continue;
    }

    if (item.dates?.includes(targetDate)) {
      return true;
    }

    if (item.currentWeekOnly && Number(item.weekId) !== Number(weekId)) {
      continue;
    }

    if (
      !item.currentWeekOnly &&
      (weekId < item.weekStart || weekId > item.weekEnd)
    ) {
      continue;
    }

    const scheduledDays = item.days
      ? item.days
          .split(",")
          .filter(Boolean)
          .map((d) => Number(d.trim()) - 2)
      : [];

    if (scheduledDays.includes(day) || item.source === "temporary") {
      if (item.source === "temporary") {
        if (Number(item.day) === Number(day)) return true;
      } else {
        return true;
      }
    }
  }

  for (const item of temporarySchedules) {
    if (
      draggedItem &&
      String(item.requiredId) === String(draggedItem.dataset.requiredId)
    ) {
      continue;
    }

    if (
      Number(item.roomId) !== Number(roomId) ||
      Number(item.session) !== Number(session)
    ) {
      continue;
    }

    if (
      removedScheduleDays.has(getScheduleDayKey(item.requiredId, day)) ||
      removedScheduleDayWeeks.has(
        getScheduleDayWeekKey(item.requiredId, day, weekId),
      )
    ) {
      continue;
    }

    const start = Number(item.weekStart || item.weekId);
    const end = Number(item.weekEnd || item.weekId);

    if (
      item.currentWeekOnly
        ? Number(item.weekId) === Number(weekId)
        : weekId >= start && weekId <= end
    ) {
      if (Number(item.day) === Number(day)) {
        return true;
      }
    }
  }

  return false;
}

// ================= LÀM MỜ CÁC Ô LỊCH KHÔNG HỢP LỆ =================

const scheduleCells = document.querySelectorAll(".schedule-cell");

function highlightInvalidCells(item) {
  const week = weeks[currentIndex];

  if (!week) return;

  scheduleCells.forEach((cell) => {
    const room = cell.closest("tr");
    const day = Number(cell.dataset.day);

    const targetDate = parseDate(week.start);
    targetDate.setDate(targetDate.getDate() + day);

    const dateString = toDateString(targetDate);

    const correctDate = checkRequestDate(
      item,
      day,
      Number(week.id),
      dateString,
    );

    const roomSuitable = checkRoomSuitableJS(room, item);

    const conflict = checkConflictJS(
      room.dataset.room,
      Number(item.dataset.session),
      day,
      Number(week.id),
      dateString,
    );

    const correctSession = String(item.dataset.session) === currentSession;

    const valid = correctSession && correctDate && roomSuitable && !conflict;

    cell.classList.toggle("invalid-cell", !valid);
    cell.dataset.invalid = valid ? "false" : "true";
  });
}

// ===========KHÔI PHỤC YÊU CẦU =============

function getRequiredDays(item) {
  if (item.dataset.date) {
    return [(parseDate(item.dataset.date).getDay() + 6) % 7];
  }

  return (item.dataset.days || "")
    .split(",")
    .filter(Boolean)
    .map((day) => Number(day.trim()) - 2);
}

function setRequestDragEffect(event, item) {
  event.dataTransfer.effectAllowed =
    getRequiredDays(item).length > 1 ? "copyMove" : "move";
  event.dataTransfer.setData("text/plain", item.dataset.requiredId);
}

function restoreRequiredItem(card) {
  const item = document.createElement("div");

  item.className = "required-item";
  item.draggable = isEditing;

  item.dataset.requiredId = card.dataset.requiredId;
  item.dataset.course = card.dataset.course;
  item.dataset.teacher = card.dataset.teacher;
  item.dataset.session = card.dataset.session;
  item.dataset.machines = card.dataset.machines;
  item.dataset.software = card.dataset.software;
  item.dataset.date = card.dataset.date || "";
  item.dataset.days = card.dataset.days || "";
  item.dataset.weekStart = card.dataset.weekStart || "";
  item.dataset.weekEnd = card.dataset.weekEnd || "";
  item.dataset.weekStartName = card.dataset.weekStartName || "";
  item.dataset.weekEndName = card.dataset.weekEndName || "";

  const sessionText =
    {
      1: "Sáng",
      2: "Chiều",
      3: "Tối",
    }[card.dataset.session] || "";

  let scheduleText = "";

  if (card.dataset.date) {
    scheduleText = card.dataset.date;
  } else {
    const dayNames = {
      2: "Thứ 2",
      3: "Thứ 3",
      4: "Thứ 4",
      5: "Thứ 5",
      6: "Thứ 6",
      7: "Thứ 7",
      8: "Chủ nhật",
    };

    const days = (card.dataset.days || "")
      .split(",")
      .map((day) => dayNames[Number(day.trim())])
      .filter(Boolean)
      .join(", ");

    const weekStart = card.dataset.weekStartName || card.dataset.weekStart;
    const weekEnd = card.dataset.weekEndName || card.dataset.weekEnd;

    scheduleText = `${days} | Tuần ${weekStart} - Tuần ${weekEnd}`;
  }

  const courseElement = document.createElement("div");
  courseElement.className = "required-item-course";
  courseElement.textContent = card.dataset.course || "";

  const teacherElement = document.createElement("div");
  teacherElement.className = "required-item-teacher";
  teacherElement.textContent = card.dataset.teacher || "";

  const timeElement = document.createElement("div");
  timeElement.className = "required-item-time";
  timeElement.textContent = `${sessionText} | ${scheduleText}`;

  item.append(courseElement, teacherElement, timeElement);

  // Gắn sự kiện kéo thả cho phần tử được khôi phục
  item.addEventListener("dragstart", (event) => {
    if (!isEditing) {
      event.preventDefault();
      return;
    }

    draggedItem = item;

    setRequestDragEffect(event, item);

    item.classList.add("dragging");
    highlightInvalidCells(item);
  });

  item.addEventListener("dragend", () => {
    item.classList.remove("dragging");

    document.querySelectorAll(".schedule-cell").forEach((cell) => {
      cell.classList.remove("invalid-cell", "drag-over");
      delete cell.dataset.invalid;
    });

    draggedItem = null;
  });

  return item;
}

// ================= KÉO THẢ ITEM =================

const requiredItems = document.querySelectorAll(".required-item");

requiredItems.forEach((item) => {
  item.addEventListener("dragstart", (event) => {
    if (!isEditing) {
      event.preventDefault();
      return;
    }

    draggedItem = item;

    setRequestDragEffect(event, item);

    item.classList.add("dragging");
    highlightInvalidCells(item);
  });

  item.addEventListener("dragend", () => {
    item.classList.remove("dragging");

    document.querySelectorAll(".schedule-cell").forEach((cell) => {
      cell.classList.remove("invalid-cell", "drag-over");
      delete cell.dataset.invalid;
    });

    draggedItem = null;
  });
});

// ================= KÉO YÊU CẦU VÀO LỊCH =================

// kiem tra sau khi keo thi con bao nhieu thu trong yc (lay thu da xep lich r)
function getAssignedDays(requiredId, weekId = Number(weeks[currentIndex]?.id)) {
  return new Set(
    temporarySchedules
      .filter((item) => {
        const day = Number(item.day);
        const matchesRequest = String(item.requiredId) === String(requiredId);
        const appliesToWeek =
          !item.currentWeekOnly || Number(item.weekId) === Number(weekId);
        const isRemoved =
          removedScheduleDays.has(getScheduleDayKey(requiredId, day)) ||
          removedScheduleDayWeeks.has(
            getScheduleDayWeekKey(requiredId, day, weekId),
          );

        return matchesRequest && appliesToWeek && !isRemoved;
      })
      .map((item) => Number(item.day)),
  );
}

// kiem tra phai thu cuoi cung cua yeu cau k (da xep du cac thu chua)
function completesPlacement(
  item,
  day,
  weekId = Number(weeks[currentIndex]?.id),
) {
  const assignedDays = getAssignedDays(item.dataset.requiredId, weekId);
  assignedDays.add(Number(day));

  return getRequiredDays(item).every((requiredDay) =>
    assignedDays.has(requiredDay),
  );
}

let pendingSchedulePlacement = null;
const scheduleScopePopup = document.getElementById(
  "popup-confirm-schedule-scope",
);

// thuc hien xep lich
function placeRequestOnCalendar(cell, item, day, weekId, currentWeekOnly) {
  const isFinalPlacement = completesPlacement(item, day, weekId);
  const requiredId = String(item.dataset.requiredId);

  clearRemovedScheduleDay(requiredId, day);

  const card = document.createElement("div");
  card.className = "scheduled-item";
  card.draggable = isEditing;
  card.textContent = `${item.dataset.course} - ${item.dataset.teacher}`;

  card.dataset.requiredId = requiredId;
  card.dataset.day = String(day);
  card.dataset.course = item.dataset.course;
  card.dataset.teacher = item.dataset.teacher;
  card.dataset.session = item.dataset.session;
  card.dataset.machines = item.dataset.machines;
  card.dataset.software = item.dataset.software;
  card.dataset.date = item.dataset.date || "";
  card.dataset.days = item.dataset.days || "";
  card.dataset.weekStart = item.dataset.weekStart || "";
  card.dataset.weekEnd = item.dataset.weekEnd || "";
  card.dataset.weekStartName = item.dataset.weekStartName || "";
  card.dataset.weekEndName = item.dataset.weekEndName || "";
  card.requiredItem = item;

  temporarySchedules.push({
    requiredId,
    roomId: Number(cell.dataset.room),
    day,
    session: Number(item.dataset.session),
    weekId,
    currentWeekOnly,
    course: item.dataset.course,
    teacher: item.dataset.teacher,
    machines: Number(item.dataset.machines),
    software: Number(item.dataset.software),
    date: item.dataset.date || "",
    days: item.dataset.days || "",
    weekStart: item.dataset.weekStart || "",
    weekEnd: item.dataset.weekEnd || "",
    weekStartName: item.dataset.weekStartName || "",
    weekEndName: item.dataset.weekEndName || "",
    requiredItem: item,
  });

  cell.appendChild(card);
  cell.dataset.occupied = "true";
  cell.dataset.requiredId = requiredId;

  if (isFinalPlacement) {
    item.remove();
  }
}

function closeScheduleScopePopup() {
  scheduleScopePopup.classList.remove("show");
  pendingSchedulePlacement = null;
}

function confirmScheduleScope(currentWeekOnly) {
  if (pendingSchedulePlacement) {
    const { cell, item, day, weekId } = pendingSchedulePlacement;
    placeRequestOnCalendar(cell, item, day, weekId, currentWeekOnly);
  }
  closeScheduleScopePopup();
}

document
  .getElementById("schedule-scope-all")
  .addEventListener("click", () => confirmScheduleScope(false));
document
  .getElementById("schedule-scope-current")
  .addEventListener("click", () => confirmScheduleScope(true));
document
  .getElementById("schedule-scope-cancel")
  .addEventListener("click", closeScheduleScopePopup);

// ================= QUÁ TRÌNH KÉO VÀO Ô LỊCH =================

scheduleCells.forEach((cell) => {
  cell.addEventListener("dragover", (event) => {
    if (!isEditing) return;

    event.preventDefault();

    const day = Number(cell.dataset.day);
    const activeItem = draggedItem || draggedScheduleCard;
    const assignedDays = activeItem
      ? getAssignedDays(activeItem.dataset.requiredId)
      : new Set();
    const isSourceCell = draggedScheduleCard?.parentElement === cell;

    if (
      !activeItem ||
      cell.dataset.invalid === "true" ||
      (cell.dataset.occupied === "true" && !isSourceCell) ||
      (draggedItem && !draggedScheduleCard && assignedDays.has(day))
    ) {
      event.dataTransfer.dropEffect = "none";
    } else {
      const week = weeks[currentIndex];
      const targetDate = parseDate(week.start);
      targetDate.setDate(targetDate.getDate() + day);
      const dateString = toDateString(targetDate);
      const validDestination =
        !draggedScheduleCard ||
        (checkRequestDate(
          draggedScheduleCard,
          day,
          Number(week.id),
          dateString,
        ) &&
          checkRoomSuitableJS(cell.closest("tr"), draggedScheduleCard) &&
          !checkConflictJS(
            cell.dataset.room,
            Number(activeItem.dataset.session),
            day,
            Number(week.id),
            dateString,
          ));

      event.dataTransfer.dropEffect = validDestination
        ? draggedScheduleCard || completesPlacement(activeItem, day)
          ? "move"
          : "copy"
        : "none";
    }

    cell.classList.add("drag-over");
  });

  cell.addEventListener("dragleave", () => {
    cell.classList.remove("drag-over");
  });

  cell.addEventListener("drop", (event) => {
    event.preventDefault();
    cell.classList.remove("drag-over");

    if (!isEditing) return;

    if (draggedScheduleCard) {
      const sourceCard = draggedScheduleCard;
      const day = Number(cell.dataset.day);
      const week = weeks[currentIndex];
      const weekId = Number(week?.id);
      const targetDate = parseDate(week.start);
      targetDate.setDate(targetDate.getDate() + day);
      const dateString = toDateString(targetDate);
      const isSourceCell = sourceCard.parentElement === cell;

      if (
        isSourceCell ||
        cell.dataset.invalid === "true" ||
        (cell.dataset.occupied === "true" && !isSourceCell) ||
        !checkRequestDate(sourceCard, day, weekId, dateString) ||
        !checkRoomSuitableJS(cell.closest("tr"), sourceCard) ||
        checkConflictJS(
          cell.dataset.room,
          Number(sourceCard.dataset.session),
          day,
          weekId,
          dateString,
        )
      ) {
        return;
      }

      const sourceDay = Number(sourceCard.dataset.day);
      const requiredId = sourceCard.dataset.requiredId;
      if (
        sourceDay !== day &&
        !sourceCard.dataset.date &&
        sourceCard.dataset.days
      ) {
        removedScheduleDayWeeks.add(
          getScheduleDayWeekKey(requiredId, sourceDay, weekId),
        );
      }

      placeRequestOnCalendar(cell, sourceCard, day, weekId, true);
      sourceCard.remove();
      renderScheduledRequests();
      return;
    }

    if (!draggedItem) return;

    const item = draggedItem;
    const day = Number(cell.dataset.day);
    const weekId = Number(weeks[currentIndex]?.id);
    const startWeek = Number(item.dataset.weekStart);
    const endWeek = Number(item.dataset.weekEnd);
    const isLongTermRequest =
      !item.dataset.date && startWeek > 0 && endWeek > startWeek;

    if (isLongTermRequest) {
      pendingSchedulePlacement = { cell, item, day, weekId };
      scheduleScopePopup.classList.add("show");
    } else {
      placeRequestOnCalendar(cell, item, day, weekId, false);
    }
  });
});

// ================= THUC THI XOA LICH =================

const requiredList = document.querySelector(".required-list");

function executeDeleteSchedule(requiredId, mode, day) {
  const currentWeekId = weeks[currentIndex]
    ? Number(weeks[currentIndex].id)
    : null;

  if (mode === "all") {
    const scheduledCards = document.querySelectorAll(
      `.scheduled-item[data-required-id="${requiredId}"]`,
    );

    if (scheduledCards.length > 0) {
      const firstCard = scheduledCards[0];
      const originalItem =
        firstCard.requiredItem || restoreRequiredItem(firstCard);
      requiredList.appendChild(originalItem);
    }

    temporarySchedules = temporarySchedules.filter(
      (item) =>
        String(item.requiredId) !== requiredId || Number(item.day) !== day,
    );
    removedScheduleDays.add(getScheduleDayKey(requiredId, day));
    removedScheduleDayWeeks.forEach((key) => {
      if (key.startsWith(`${getScheduleDayKey(requiredId, day)}:`)) {
        removedScheduleDayWeeks.delete(key);
      }
    });

    renderScheduledRequests();
  } else if (mode === "current_week") {
    removedScheduleDayWeeks.add(
      getScheduleDayWeekKey(requiredId, day, currentWeekId),
    );

    renderScheduledRequests();
  }
}

// ================= KÉO LỊCH VỀ DANH SÁCH =================

let pendingDeleteRequiredId = null; //ma yc cho xoa
let pendingDeleteDay = null; //thu cho xoa
let draggedScheduleDay = null; //thu cua the dang keo
let draggedScheduleCard = null;

requiredList.addEventListener("dragover", (event) => {
  if (!isEditing) return;

  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
});

requiredList.addEventListener("drop", (event) => {
  event.preventDefault();

  if (!isEditing) return;

  const requiredId = String(event.dataTransfer.getData("text/plain"));
  const scheduledCards = document.querySelectorAll(
    `.scheduled-item[data-required-id="${requiredId}"]`,
  );

  if (scheduledCards.length === 0) return;

  const firstCard = scheduledCards[0];
  const draggedDay = draggedScheduleDay;

  if (!Number.isInteger(draggedDay)) return;

  // Kiểm tra xem yêu cầu này có kéo dài nhiều tuần không
  const weekStart = Number(firstCard.dataset.weekStart);
  const weekEnd = Number(firstCard.dataset.weekEnd);
  const spansMultipleWeeks = weekStart && weekEnd && weekStart !== weekEnd;

  pendingDeleteRequiredId = requiredId;
  pendingDeleteDay = draggedDay;

  if (spansMultipleWeeks) {
    popupConfirmDelete.classList.add("show");
  } else {
    executeDeleteSchedule(requiredId, "all", draggedDay);
  }
});

// ===============CAC BTN ==============

const btnDeleteAll = document.getElementById("btn-delete-all");
btnDeleteAll.addEventListener("click", () => {
  if (pendingDeleteRequiredId) {
    executeDeleteSchedule(pendingDeleteRequiredId, "all", pendingDeleteDay);
  }
  closeConfirmPopup();
});

const btnDeleteOne = document.getElementById("btn-delete-one");
btnDeleteOne.addEventListener("click", () => {
  if (pendingDeleteRequiredId) {
    executeDeleteSchedule(
      pendingDeleteRequiredId,
      "current_week",
      pendingDeleteDay,
    );
  }
  closeConfirmPopup();
});

const popupConfirmDelete = document.getElementById("popup-confirm-delete");
function closeConfirmPopup() {
  popupConfirmDelete.classList.remove("show");
  pendingDeleteRequiredId = null;
  pendingDeleteDay = null;
}

const btnDeleteCancel = document.getElementById("btn-delete-cancel");
btnDeleteCancel.addEventListener("click", closeConfirmPopup);

// ================= KÉO THẺ LỊCH =================

document.addEventListener("dragstart", (event) => {
  const card = event.target.closest(".scheduled-item");

  if (!card) return;
  if (!isEditing) {
    event.preventDefault();
    return;
  }

  draggedScheduleDay = Number(card.dataset.day);
  draggedScheduleCard = card;
  draggedItem = card;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", card.dataset.requiredId);
  highlightInvalidCells(card);
});

document.addEventListener("dragend", () => {
  if (draggedScheduleCard) {
    draggedItem = null;
    document.querySelectorAll(".schedule-cell").forEach((cell) => {
      cell.classList.remove("invalid-cell", "drag-over");
      delete cell.dataset.invalid;
    });
  }
  draggedScheduleCard = null;
  draggedScheduleDay = null;
});

// ================= AUTO SCROLL KHI KÉO =================

const calendarTable = document.querySelector(".calendar-table");

let autoScrollInterval = null;

document.addEventListener("dragover", function (event) {
  const isDraggingCalendarItem =
    isEditing && (draggedItem || Number.isInteger(draggedScheduleDay));

  if (
    !isDraggingCalendarItem ||
    !calendarTable ||
    calendarTable.scrollHeight <= calendarTable.clientHeight
  ) {
    stopAutoScroll();
    return;
  }

  const rect = calendarTable.getBoundingClientRect();
  const visibleTop = Math.max(rect.top, 0);
  const visibleBottom = Math.min(rect.bottom, window.innerHeight);
  const mouseY = event.clientY;

  const edgeSize = 80; // vung kich hoat ham
  const scrollSpeed = 12; // toc do cuon

  clearInterval(autoScrollInterval);
  autoScrollInterval = null;

  // Kéo gần mép dưới: cuộn xuống
  if (
    mouseY > visibleBottom - edgeSize &&
    mouseY < visibleBottom &&
    event.clientX >= rect.left &&
    event.clientX <= rect.right
  ) {
    autoScrollInterval = setInterval(() => {
      calendarTable.scrollTop += scrollSpeed;
    }, 16);
  }

  // Kéo gần mép trên: cuộn lên
  else if (
    mouseY < visibleTop + edgeSize &&
    mouseY > visibleTop &&
    event.clientX >= rect.left &&
    event.clientX <= rect.right
  ) {
    autoScrollInterval = setInterval(() => {
      calendarTable.scrollTop -= scrollSpeed;
    }, 16);
  }
});

document.addEventListener("dragend", stopAutoScroll);
document.addEventListener("drop", stopAutoScroll);

function stopAutoScroll() {
  clearInterval(autoScrollInterval);
  autoScrollInterval = null;
}

// ================= CHỈNH SỬA LỊCH =================

const editBtn = document.getElementById("editBtn");
const cancelBtn = document.getElementById("cancelBtn");
const saveBtn = document.getElementById("saveBtn");
const cancelEditPopup = document.getElementById("popup-cancel-edit");
const cancelEditStayBtn = document.getElementById("cancel-edit-stay");
const cancelEditDiscardBtn = document.getElementById("cancel-edit-discard");

function setEditingMode(editing) {
  isEditing = editing;
  requiredList.classList.toggle("is-locked", !editing);
  requiredList.setAttribute("aria-disabled", String(!editing));

  requiredList.querySelectorAll(".required-item").forEach((item) => {
    item.draggable = editing;
  });
  document.querySelectorAll(".scheduled-item").forEach((item) => {
    item.draggable = editing;
  });

  editBtn.hidden = editing;
  cancelBtn.hidden = !editing;
  saveBtn.hidden = !editing;
}

editBtn.addEventListener("click", () => {
  setEditingMode(true);
});

saveBtn.addEventListener("click", async () => {
  saveBtn.disabled = true;

  try {
    const response = await fetch("/admin/calendar/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schedules: temporarySchedules.map((schedule) => ({
          requiredId: schedule.requiredId,
          roomId: schedule.roomId,
          day: schedule.day,
          weekId: schedule.weekId,
          currentWeekOnly: Boolean(schedule.currentWeekOnly),
        })),
        removedDays: Array.from(removedScheduleDays),
        removedDayWeeks: Array.from(removedScheduleDayWeeks),
      }),
    });
    const result = await response.json().catch(() => ({}));

    if (!response.ok || !result.success) {
      showErrorPopup(result.message || "Không thể lưu lịch thực hành.");
      return;
    }

    window.location.reload();
  } catch (error) {
    console.error("Lỗi khi lưu lịch thực hành:", error);
    showErrorPopup("Không thể kết nối để lưu lịch thực hành.");
  } finally {
    saveBtn.disabled = false;
  }
});

cancelBtn.addEventListener("click", () => {
  cancelEditPopup.classList.add("show");
});

cancelEditStayBtn.addEventListener("click", () => {
  cancelEditPopup.classList.remove("show");
});

cancelEditDiscardBtn.addEventListener("click", () => {
  window.location.reload();
});

setEditingMode(false);
