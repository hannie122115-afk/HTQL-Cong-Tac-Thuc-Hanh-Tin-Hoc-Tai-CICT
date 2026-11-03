const weeks = JSON.parse(document.getElementById("weeks-data").textContent);
const scheduledRequests = JSON.parse(
  document.getElementById("scheduled-data").textContent,
);

function parseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDate(date) {
  return `${String(date.getDate()).padStart(2, "0")}/${String(
    date.getMonth() + 1,
  ).padStart(2, "0")}`;
}

// lay thứ
function getDayIndex(dateString) {
  return (parseDate(dateString).getDay() + 6) % 7;
}

function isWithinWeek(dateString, week) {
  return dateString >= week.start && dateString <= week.end;
}

function getOccurrences(schedule, week) {
  const occurrences = new Map();
  const addOccurrence = (date) => {
    if (date && isWithinWeek(date, week)) {
      occurrences.set(date, getDayIndex(date));
    }
  };

  (schedule.DanhSachNgay || "")
    .split(",")
    .filter(Boolean)
    .forEach(addOccurrence);

  if (
    schedule.LaLichDinhKy &&
    Number(schedule.MaTuanBatDau) <= Number(week.id) &&
    Number(schedule.MaTuanKetThuc) >= Number(week.id)
  ) {
    (schedule.DanhSachThu || "")
      .split(",")
      .filter(Boolean)
      .forEach((weekday) => {
        const day = Number(weekday.trim()) - 2;
        if (day >= 0 && day <= 6) {
          occurrences.set(`recurring-${day}`, day);
        }
      });
  }

  return occurrences;
}

let currentIndex = -1;
const sessionButtons = document.querySelectorAll(".session-btn");
const savedSession = sessionStorage.getItem("teacherCalendarSession");
let currentSession = ["1", "2", "3"].includes(savedSession)
  ? savedSession
  : "1";
const dayElements = document.querySelectorAll(".day-of-week");
const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const weekName = document.getElementById("weekName");
const weekSpace = document.getElementById("week-space");

function renderCalendarWeek() {
  if (currentIndex < 0 || !weeks.length) {
    weekName.textContent = "Chưa có dữ liệu tuần học";
    weekSpace.textContent = "";
    previousWeek.disabled = true;
    nextWeek.disabled = true;
    dayElements.forEach((element) => {
      element.textContent = "";
    });
    return;
  }

  const week = weeks[currentIndex];
  weekName.textContent = week.name;
  weekSpace.textContent = `${formatDate(parseDate(week.start))} - ${formatDate(
    parseDate(week.end),
  )}`;

  dayElements.forEach((element) => {
    const date = parseDate(week.start);
    date.setDate(date.getDate() + Number(element.dataset.day));
    element.textContent = `(${formatDate(date)})`;
  });

  previousWeek.disabled = currentIndex === 0;
  nextWeek.disabled = currentIndex === weeks.length - 1;
}

function renderScheduledRequests() {
  document.querySelectorAll(".schedule-cell").forEach((cell) => {
    cell.replaceChildren();
    cell.dataset.session = currentSession;
  });

  if (currentIndex < 0 || !weeks.length) return;

  const week = weeks[currentIndex];
  scheduledRequests.forEach((schedule) => {
    const session = Number(schedule.BuoiThucHanh);
    if (session < 1 || session > 3) return;

    getOccurrences(schedule, week).forEach((day) => {
      const cell = document.querySelector(
        `.schedule-cell[data-room="${schedule.MaPhong}"]` +
          `[data-day="${day}"][data-session="${session}"]`,
      );
      if (!cell) return;

      const card = document.createElement("div");
      card.className = "scheduled-item";
      const course = document.createElement("div");
      course.className = "scheduled-item-course";
      course.textContent = schedule.TenHocPhan || "Lịch thực hành";
      card.appendChild(course);

      if (schedule.NhomHocPhan) {
        const group = document.createElement("div");
        group.className = "scheduled-item-group";
        group.textContent = `Nhóm: ${schedule.NhomHocPhan}`;
        card.appendChild(group);
      }

      card.title = `Mã yêu cầu: ${schedule.MaYeuCau}`;
      cell.appendChild(card);
    });
  });
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

currentIndex = findCurrentWeek();
if (currentIndex < 0 && weeks.length) currentIndex = 0;

previousWeek.addEventListener("click", () => {
  if (currentIndex > 0) {
    currentIndex -= 1;
    renderCalendarWeek();
    renderScheduledRequests();
  }
});

nextWeek.addEventListener("click", () => {
  if (currentIndex < weeks.length - 1) {
    currentIndex += 1;
    renderCalendarWeek();
    renderScheduledRequests();
  }
});

function changeSession(session) {
  currentSession = session;
  sessionStorage.setItem("teacherCalendarSession", session);
  sessionButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.session === session);
  });
  renderScheduledRequests();
}

sessionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    changeSession(button.dataset.session);
  });
});

renderCalendarWeek();
changeSession(currentSession);

const popupSuccess = document.getElementById("popup-success");
const calendarPage = document.getElementById("calendar-page");

if (popupSuccess && calendarPage?.dataset.success) {
  popupSuccess.classList.add("show");
  setTimeout(() => {
    window.location.reload();
  }, 300);
}
