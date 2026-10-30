const weeks = JSON.parse(document.getElementById("weeks-data").textContent);
const scheduledRequests = JSON.parse(
  document.getElementById("scheduled-data").textContent,
);
// Các lịch mới được kéo thả, chưa lưu xuống database
let demoSchedules = [];

// Các mã yêu cầu đã được kéo từ lịch về danh sách
let removedScheduleIds = new Set();

const weekName = document.getElementById("weekName");
const weekSpace = document.getElementById("week-space");
const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const dayElements = document.querySelectorAll(".day-of-week");

const today = new Date();

function getMonday(date) {
  const monday = new Date(date);
  const day = monday.getDay();

  // trừ đi số ngày để tìm về thứ Hai
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

let currentIndex = -1;

// ===============vẽ lại các yêu cầu trong tuần khi có thay đổi
function renderScheduledRequests() {
  // Xóa lịch đang hiển thị trước khi vẽ tuần mới
  document.querySelectorAll(".schedule-cell").forEach((cell) => {
    cell.innerHTML = "";
    delete cell.dataset.occupied;
    delete cell.dataset.requiredId;
  });

  if (currentIndex < 0 || !weeks.length) return;

  const currentWeek = weeks[currentIndex];

  scheduledRequests.forEach((item) => {
    if (removedScheduleIds.has(String(item.MaYeuCau))) {
      return;
    }
    // Chỉ hiển thị lịch thuộc tuần đang xem
    const isSpecificDate = Boolean(item.NgayThucHanh);

    if (isSpecificDate) {
      const date = item.NgayThucHanh;
      if (date < currentWeek.start || date > currentWeek.end) return;
    } else {
      if (
        item.MaTuanBatDau > currentWeek.id ||
        item.MaTuanKetThuc < currentWeek.id
      ) {
        return;
      }
    }

    // Xác định thứ thực hành
    let days = [];

    if (isSpecificDate) {
      const date = parseDate(item.NgayThucHanh);
      // Thứ 2 = 0, ..., Chủ nhật = 6
      // getDay trong js => lấy thứ
      days = [(date.getDay() + 6) % 7];
    } else {
      days = (item.DanhSachThu || "")
        .split(",")
        .filter(Boolean)
        .map((day) => Number(day) - 2);
    }

    days.forEach((day) => {
      if (day < 0 || day > 6) return;

      const cell = document.querySelector(
        `.schedule-cell[data-room="${item.MaPhong}"]` + `[data-day="${day}"]`,
      );

      if (!cell) return;

      const card = document.createElement("div");
      card.className = "scheduled-item";
      card.draggable = true;
      card.textContent = `${item.TenHocPhan} - ${item.TenGiangVien}`;

      card.dataset.requiredId = item.MaYeuCau;
      card.dataset.course = item.TenHocPhan;
      card.dataset.teacher = item.TenGiangVien;
      card.dataset.session = item.BuoiThucHanh;
      card.dataset.machines = item.SoLuongMay;
      card.dataset.software = item.MaPhanMem;
      card.dataset.date = item.NgayThucHanh || "";
      card.dataset.days = item.DanhSachThu || "";
      card.dataset.weekStart = item.MaTuanBatDau || "";
      card.dataset.weekEnd = item.MaTuanKetThuc || "";

      if (String(item.BuoiThucHanh) === currentSession) {
        cell.appendChild(card);
        cell.dataset.occupied = "true";
        cell.dataset.requiredId = item.MaYeuCau;
      }
    });
  });
}

// ====================lấy ngày trong tuần
function renderCalendarWeek() {
  if (weeks.length === 0 || currentIndex < 0) {
    weekName.textContent = "Chưa có dữ liệu tuần học";
    previousWeek.disabled = true;
    nextWeek.disabled = true;

    dayElements.forEach(function (element) {
      element.textContent = "";
    });

    return;
  }

  const week = weeks[currentIndex];
  weekName.textContent = `${week.name}`;
  weekSpace.textContent = `${formatDate(parseDate(week.start))} - ${formatDate(parseDate(week.end))}`;

  dayElements.forEach(function (element) {
    const dayIndex = Number(element.dataset.day);
    const date = parseDate(week.start);
    // lấy ngày đầu tiên + thêm index nữa để ra các ngày kế
    date.setDate(date.getDate() + dayIndex);
    element.textContent = `(${formatDate(date)})`;
  });

  previousWeek.disabled = currentIndex === 0;
  nextWeek.disabled = currentIndex === weeks.length - 1;
}

function findCurrentWeek() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);

  return weeks.findIndex(function (week) {
    const start = parseDate(week.start);
    const end = parseDate(week.end);

    return now >= start && now <= end;
  });
}

previousWeek.addEventListener("click", function () {
  if (currentIndex > 0) {
    currentIndex--;
    renderCalendarWeek();
    renderScheduledRequests();
  }
});

nextWeek.addEventListener("click", function () {
  if (currentIndex < weeks.length - 1) {
    currentIndex++;
    renderCalendarWeek();
    renderScheduledRequests();
  }
});

currentIndex = findCurrentWeek();
if (currentIndex === -1 && weeks.length > 0) {
  currentIndex = 0;
}

// ================= CHỌN BUỔI =================

const sessionBtn = document.querySelectorAll(".session-btn");
const calendarBody = document.getElementById("calendar-body");

let currentSession = "1";

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

// =======POPUP ============
const popupError = document.getElementById("popup-error");
const popupMessageError = document.getElementById("popup-error-message");
const popupErrorClose = document.getElementById("popup-error-close");

function showErrorPopup(message) {
  popupMessageError.textContent = message;
  popupError.classList.add("show");
}

popupErrorClose.addEventListener("click", function () {
  popupError.classList.remove("show");
});

// ============== KÉO THẢ ITEM =========
const requiredItems = document.querySelectorAll(".required-item");
const scheduleCells = document.querySelectorAll(".schedule-cell");
const sessionButtons = document.querySelectorAll(".session-btn");

function restoreRequiredItem(card) {
  const item = document.createElement("div");

  item.className = "required-item";
  item.draggable = true;

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

  const sessionText =
    card.dataset.session === "1"
      ? "Sáng"
      : card.dataset.session === "2"
        ? "Chiều"
        : "Tối";

  let scheduleText = "";

  if (card.dataset.date) {
    scheduleText = card.dataset.date;
  } else {
    const days = (card.dataset.days || "")
      .split(",")
      .filter(Boolean)
      .join(", ");

    const weekStart = card.dataset.weekStart;
    const weekEnd = card.dataset.weekEnd;

    scheduleText = `
    ${days}
    <span></span>
    Tuần ${weekStart} - Tuần ${weekEnd}
  `;
  }

  item.innerHTML = `
  <div class="required-item-course">
    ${card.dataset.course}
  </div>
  <div class="required-item-teacher">
    ${card.dataset.teacher}
  </div>
  <div class="required-item-time">
    ${sessionText}
    <span></span>
    ${scheduleText}
  </div>
  `;

  item.addEventListener("dragstart", (event) => {
    draggedItem = item;

    event.dataTransfer.effectAllowed = "move"; //di chuyển luôn
    event.dataTransfer.setData("text/plain", item.dataset.requiredId);

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

let draggedItem = null;

// Kéo yêu cầu từ danh sách
requiredItems.forEach((item) => {
  item.addEventListener("dragstart", (event) => {
    draggedItem = item;

    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", item.dataset.requiredId);

    item.classList.add("dragging");

    highlightInvalidCells(item);
  });

  item.addEventListener("dragend", () => {
    item.classList.remove("dragging");

    document.querySelectorAll(".schedule-cell").forEach((cell) => {
      cell.classList.remove("invalid-cell");
      cell.classList.remove("drag-over");
      delete cell.dataset.invalid;
    });

    draggedItem = null;
  });
});

scheduleCells.forEach((cell) => {
  cell.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    cell.classList.add("drag-over");
  });

  cell.addEventListener("dragleave", () => {
    cell.classList.remove("drag-over");
  });

  cell.addEventListener("drop", (event) => {
    event.preventDefault();
    cell.classList.remove("drag-over");

    if (!draggedItem) return;

    if (cell.dataset.invalid === "true") {
      showErrorPopup("Phòng hoặc thời gian thực hành không phù hợp.");
      return;
    }

    if (draggedItem.dataset.session !== currentSession) {
      showErrorPopup("Yêu cầu này không thuộc buổi đang chọn.");
      return;
    }

    if (cell.dataset.occupied === "true") {
      showErrorPopup("Ô lịch này đã có yêu cầu.");
      return;
    }

    const course = draggedItem.dataset.course;
    const teacher = draggedItem.dataset.teacher;
    const requiredId = draggedItem.dataset.requiredId;

    const card = document.createElement("div");
    card.className = "scheduled-item";
    card.draggable = true;
    card.textContent = `${course} - ${teacher}`;

    card.dataset.requiredId = draggedItem.dataset.requiredId;
    card.dataset.course = draggedItem.dataset.course;
    card.dataset.teacher = draggedItem.dataset.teacher;
    card.dataset.session = draggedItem.dataset.session;
    card.dataset.machines = draggedItem.dataset.machines;
    card.dataset.software = draggedItem.dataset.software;
    card.dataset.date = draggedItem.dataset.date || "";
    card.dataset.days = draggedItem.dataset.days || "";
    card.dataset.weekStart = draggedItem.dataset.weekStart || "";
    card.dataset.weekEnd = draggedItem.dataset.weekEnd || "";

    card.requiredItem = draggedItem;

    demoSchedules.push({
      requiredId: card.dataset.requiredId,
      roomId: Number(cell.dataset.room),
      day: Number(cell.dataset.day),
      session: Number(card.dataset.session),
      weekId: weeks[currentIndex].id,

      course: card.dataset.course,
      teacher: card.dataset.teacher,
      machines: Number(card.dataset.machines),
      software: Number(card.dataset.software),

      date: card.dataset.date || "",
      days: card.dataset.days || "",
      weekStart: card.dataset.weekStart || "",
      weekEnd: card.dataset.weekEnd || "",
    });

    card.addEventListener("dragstart", (event) => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", requiredId);
    });

    cell.appendChild(card);
    cell.dataset.occupied = "true";
    cell.dataset.requiredId = requiredId;

    draggedItem.remove();
  });
});

const requiredList = document.querySelector(".required-list");

requiredList.addEventListener("dragover", (event) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
});

requiredList.addEventListener("drop", (event) => {
  event.preventDefault();

  const requiredId = event.dataTransfer.getData("text/plain");

  const scheduledCards = document.querySelector(
    `.scheduled-item[data-required-id="${requiredId}"]`,
  );

  if (!scheduledCards.length === 0) return;

  // Lấy một thẻ để khôi phục thông tin yêu cầu
  const originalItem =
    scheduledCards[0].requiredItem || restoreRequiredItem(scheduledCards[0]);
  requiredList.appendChild(originalItem);

  removedScheduleIds.add(String(requiredId));

  // Xóa tất cả thẻ lịch thuộc cùng yêu cầu
  scheduledCards.forEach((card) => {
    const cell = card.closest(".schedule-cell");

    card.remove();

    if (cell) {
      delete cell.dataset.occupied;
      delete cell.dataset.requiredId;
    }
  });
});

document.addEventListener("dragstart", (event) => {
  const card = event.target.closest(".scheduled-item");

  if (!card) return;

  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", card.dataset.requiredId);
});

// ============= LÀM MƠG CÁC Ô LỊCH
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

// =========== CHECK TRÙNG PHÒNG =====
function checkConflictJS(roomId, session, day, weekId, targetDate) {
  for (const item of scheduledRequests) {
    if (
      Number(item.MaPhong) !== Number(roomId) ||
      Number(item.BuoiThucHanh) !== session
    ) {
      continue;
    }

    if (item.NgayThucHanh) {
      if (item.NgayThucHanh === targetDate) {
        return true;
      }
      continue;
    }

    const startWeek = Number(item.MaTuanBatDau);
    const endWeek = Number(item.MaTuanKetThuc);

    if (weekId < startWeek || weekId > endWeek) {
      continue;
    }

    const scheduledDays = (item.DanhSachThu || "")
      .split(",")
      .filter(Boolean)
      .map((d) => Number(d) - 2);

    if (scheduledDays.includes(day)) {
      return true;
    }
  }

  return false;
}

// ================= CHECK PHẢI KÉO ĐÚNG THỜI GIAN TRONG YÊU CẦU ========
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
    .map((d) => Number(d) - 2);

  return requiredDays.includes(day);
}

// ============== CÁC Ô KHÔNG HỢP LỆ ====
function highlightInvalidCells(item) {
  const week = weeks[currentIndex];

  if (!week) return;

  scheduleCells.forEach((cell) => {
    const room = cell.closest("tr");

    const day = Number(cell.dataset.day);

    const targetDate = parseDate(week.start);
    targetDate.setDate(targetDate.getDate() + day);

    const dateString = [
      targetDate.getFullYear(),
      String(targetDate.getMonth() + 1).padStart(2, "0"),
      String(targetDate.getDate()).padStart(2, "0"),
    ].join("-");

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
