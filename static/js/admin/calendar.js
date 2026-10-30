const weeks = JSON.parse(document.getElementById("weeks-data").textContent);

const scheduledRequests = JSON.parse(
  document.getElementById("scheduled-data").textContent,
);

// Các lịch mới được kéo thả, chưa lưu xuống database
let temporarySchedules = [];

// Các mã yêu cầu đã được kéo từ lịch database về danh sách
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

let currentIndex = -1;
let currentSession = "1";

// ================= LẤY DANH SÁCH LỊCH =================

function getAllSchedules() {
  // Lịch lấy từ database, bỏ qua các yêu cầu đã kéo về danh sách
  const databaseSchedules = scheduledRequests
    .filter((item) => !removedScheduleIds.has(String(item.MaYeuCau)))
    .map((item) => ({
      source: "database",
      requiredId: String(item.MaYeuCau),
      roomId: Number(item.MaPhong),
      session: Number(item.BuoiThucHanh),
      date: item.NgayThucHanh || "",
      days: item.DanhSachThu || "",
      weekStart: Number(item.MaTuanBatDau),
      weekEnd: Number(item.MaTuanKetThuc),
    }));

  // Lịch mới được kéo thả
  const newSchedules = temporarySchedules.map((item) => ({
    source: "temporary",
    requiredId: String(item.requiredId),
    roomId: Number(item.roomId),
    session: Number(item.session),
    date: item.date || "",
    days: item.days || "",
    weekStart: Number(item.weekStart),
    weekEnd: Number(item.weekEnd),
    weekId: Number(item.weekId),
    day: Number(item.day),
  }));

  return [...databaseSchedules, ...newSchedules];
}

// ================= VẼ LỊCH =================

function renderScheduledRequests() {
  // Xóa lịch đang hiển thị trước khi vẽ lại
  document.querySelectorAll(".schedule-cell").forEach((cell) => {
    cell.innerHTML = "";
    delete cell.dataset.occupied;
    delete cell.dataset.requiredId;
  });

  if (currentIndex < 0 || !weeks.length) return;

  const currentWeek = weeks[currentIndex];

  // Lấy cả lịch database và lịch tạm
  const allSchedules = getAllSchedules();

  allSchedules.forEach((schedule) => {
    let days = [];

    // Lấy dữ liệu gốc nếu là lịch database
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

    // Kiểm tra lịch có thuộc tuần đang xem không
    if (schedule.date) {
      if (
        schedule.date < currentWeek.start ||
        schedule.date > currentWeek.end
      ) {
        return;
      }
    } else {
      if (
        schedule.weekStart > currentWeek.id ||
        schedule.weekEnd < currentWeek.id
      ) {
        return;
      }
    }

    // Xác định các ngày thực hành
    if (schedule.date) {
      const date = parseDate(schedule.date);
      days = [(date.getDay() + 6) % 7];
    } else {
      days = schedule.days
        .split(",")
        .filter(Boolean)
        .map((day) => Number(day.trim()) - 2);
    }

    // Với lịch tạm, chỉ hiển thị ở đúng tuần và đúng ngày đã xếp
    if (schedule.source === "temporary") {
      days = [schedule.day];

      if (Number(schedule.weekId) !== Number(currentWeek.id)) {
        return;
      }
    }

    days.forEach((day) => {
      if (day < 0 || day > 6) return;

      const cell = document.querySelector(
        `.schedule-cell[data-room="${schedule.roomId}"][data-day="${day}"]`,
      );

      if (!cell) return;

      if (schedule.session !== Number(currentSession)) return;

      const card = document.createElement("div");
      card.className = "scheduled-item";
      card.draggable = true;

      const course = item.TenHocPhan || item.course || "";
      const teacher = item.TenGiangVien || item.teacher || "";

      card.textContent = `${course} - ${teacher}`;

      card.dataset.requiredId = schedule.requiredId;
      card.dataset.course = course;
      card.dataset.teacher = teacher;
      card.dataset.session = schedule.session;
      card.dataset.machines = item.SoLuongMay || item.machines || "";
      card.dataset.software = item.MaPhanMem || item.software || "";
      card.dataset.date = schedule.date;
      card.dataset.days = schedule.days;
      card.dataset.weekStart = schedule.weekStart || "";
      card.dataset.weekEnd = schedule.weekEnd || "";

      // Lưu tên tuần nếu dữ liệu có sẵn
      card.dataset.weekStartName = item.TuanBatDau || item.weekStartName || "";
      card.dataset.weekEndName = item.TuanKetThuc || item.weekEndName || "";

      // Giữ tham chiếu đến phần tử yêu cầu nếu là lịch tạm
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

function findCurrentWeek() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);

  return weeks.findIndex((week) => {
    const start = parseDate(week.start);
    const end = parseDate(week.end);

    return now >= start && now <= end;
  });
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
  popupMessageError.textContent = message;
  popupError.classList.add("show");
}

popupErrorClose.addEventListener("click", () => {
  popupError.classList.remove("show");
});

// ================= KÉO THẢ ITEM =================

const requiredItems = document.querySelectorAll(".required-item");
const scheduleCells = document.querySelectorAll(".schedule-cell");

let draggedItem = null;

// ================= KHÔI PHỤC YÊU CẦU =================

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

  // Tạo nội dung an toàn bằng textContent
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
    draggedItem = item;

    event.dataTransfer.effectAllowed = "move";
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

// Gắn sự kiện kéo cho các yêu cầu ban đầu
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
      cell.classList.remove("invalid-cell", "drag-over");
      delete cell.dataset.invalid;
    });

    draggedItem = null;
  });
});

// ================= KÉO YÊU CẦU VÀO LỊCH =================

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

    const requiredId = String(draggedItem.dataset.requiredId);

    // Nếu kéo lại một yêu cầu đã có trong database,
    // bỏ đánh dấu đã xóa để lịch có thể được xếp lại
    removedScheduleIds.delete(requiredId);

    // Nếu đã tồn tại lịch tạm của yêu cầu này thì xóa bản cũ
    temporarySchedules = temporarySchedules.filter(
      (item) => String(item.requiredId) !== requiredId,
    );

    const card = document.createElement("div");

    card.className = "scheduled-item";
    card.draggable = true;
    card.textContent = `${draggedItem.dataset.course} - ${draggedItem.dataset.teacher}`;

    card.dataset.requiredId = requiredId;
    card.dataset.course = draggedItem.dataset.course;
    card.dataset.teacher = draggedItem.dataset.teacher;
    card.dataset.session = draggedItem.dataset.session;
    card.dataset.machines = draggedItem.dataset.machines;
    card.dataset.software = draggedItem.dataset.software;
    card.dataset.date = draggedItem.dataset.date || "";
    card.dataset.days = draggedItem.dataset.days || "";
    card.dataset.weekStart = draggedItem.dataset.weekStart || "";
    card.dataset.weekEnd = draggedItem.dataset.weekEnd || "";
    card.dataset.weekStartName = draggedItem.dataset.weekStartName || "";
    card.dataset.weekEndName = draggedItem.dataset.weekEndName || "";

    // Lưu phần tử yêu cầu ban đầu
    card.requiredItem = draggedItem;

    // Lưu lịch mới vào mảng tạm
    temporarySchedules.push({
      requiredId,
      roomId: Number(cell.dataset.room),
      day: Number(cell.dataset.day),
      session: Number(draggedItem.dataset.session),
      weekId: Number(weeks[currentIndex].id),

      course: draggedItem.dataset.course,
      teacher: draggedItem.dataset.teacher,
      machines: Number(draggedItem.dataset.machines),
      software: Number(draggedItem.dataset.software),

      date: draggedItem.dataset.date || "",
      days: draggedItem.dataset.days || "",
      weekStart: draggedItem.dataset.weekStart || "",
      weekEnd: draggedItem.dataset.weekEnd || "",
      weekStartName: draggedItem.dataset.weekStartName || "",
      weekEndName: draggedItem.dataset.weekEndName || "",

      requiredItem: draggedItem,
    });

    cell.appendChild(card);
    cell.dataset.occupied = "true";
    cell.dataset.requiredId = requiredId;

    draggedItem.remove();
  });
});

// ================= KÉO LỊCH VỀ DANH SÁCH =================

const requiredList = document.querySelector(".required-list");

requiredList.addEventListener("dragover", (event) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
});

requiredList.addEventListener("drop", (event) => {
  event.preventDefault();

  const requiredId = String(event.dataTransfer.getData("text/plain"));

  // Tìm tất cả thẻ lịch có cùng mã yêu cầu
  const scheduledCards = document.querySelectorAll(
    `.scheduled-item[data-required-id="${requiredId}"]`,
  );

  if (scheduledCards.length === 0) return;

  const firstCard = scheduledCards[0];

  const originalItem = firstCard.requiredItem || restoreRequiredItem(firstCard);

  requiredList.appendChild(originalItem);

  // Kiểm tra yêu cầu này có phải lịch tạm không
  const isTemporary = temporarySchedules.some(
    (item) => String(item.requiredId) === requiredId,
  );

  if (isTemporary) {
    // Xóa lịch tạm khỏi danh sách
    temporarySchedules = temporarySchedules.filter(
      (item) => String(item.requiredId) !== requiredId,
    );
  } else {
    // Đánh dấu lịch database đã được kéo về danh sách
    removedScheduleIds.add(requiredId);
  }

  // Xóa toàn bộ thẻ lịch cùng mã yêu cầu đang hiển thị
  scheduledCards.forEach((card) => {
    const cell = card.closest(".schedule-cell");

    card.remove();

    if (cell) {
      delete cell.dataset.occupied;
      delete cell.dataset.requiredId;
    }
  });
});

// ================= KÉO THẺ LỊCH =================

document.addEventListener("dragstart", (event) => {
  const card = event.target.closest(".scheduled-item");

  if (!card) return;

  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", card.dataset.requiredId);
});

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

function checkConflictJS(roomId, session, day, weekId, targetDate) {
  const allSchedules = getAllSchedules();

  for (const item of allSchedules) {
    // Không xét chính yêu cầu đang được kéo
    if (
      draggedItem &&
      String(item.requiredId) === String(draggedItem.dataset.requiredId)
    ) {
      continue;
    }

    // Phải cùng phòng và cùng buổi mới có xung đột
    if (
      Number(item.roomId) !== Number(roomId) ||
      Number(item.session) !== Number(session)
    ) {
      continue;
    }

    // Lịch thực hành theo ngày cụ thể
    if (item.date) {
      if (item.date === targetDate) {
        return true;
      }

      continue;
    }

    // Lịch thực hành định kỳ
    if (weekId < item.weekStart || weekId > item.weekEnd) {
      continue;
    }

    // Kiểm tra thứ thực hành
    const scheduledDays = item.days
      .split(",")
      .filter(Boolean)
      .map((d) => Number(d.trim()) - 2);

    if (scheduledDays.includes(day)) {
      return true;
    }
  }

  // Kiểm tra thêm các lịch tạm
  for (const item of temporarySchedules) {
    // Bỏ qua chính yêu cầu đang được kéo
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

    // Lịch tạm chỉ được xếp vào tuần cụ thể
    if (Number(item.weekId) !== Number(weekId)) {
      continue;
    }

    if (Number(item.day) === Number(day)) {
      return true;
    }
  }

  return false;
}

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

// ================= LÀM MỜ CÁC Ô LỊCH KHÔNG HỢP LỆ =================

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

// ================= AUTO SCROLL KHI KÉO =================

const calendarTable = document.querySelector(".calendar-table");

let autoScrollInterval = null;

document.addEventListener("dragover", function (e) {
  if (!draggedItem || !calendarTable) return;

  const rect = calendarTable.getBoundingClientRect();
  const mouseY = e.clientY;

  const edgeSize = 80;
  const scrollSpeed = 12;

  clearInterval(autoScrollInterval);
  autoScrollInterval = null;

  // Kéo gần mép dưới: cuộn xuống
  if (mouseY > rect.bottom - edgeSize && mouseY < rect.bottom) {
    autoScrollInterval = setInterval(() => {
      calendarTable.scrollTop += scrollSpeed;
    }, 16);
  }

  // Kéo gần mép trên: cuộn lên
  else if (mouseY < rect.top + edgeSize && mouseY > rect.top) {
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
