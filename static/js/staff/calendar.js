const weeks = JSON.parse(document.getElementById("weeks-data").textContent);
const assignments = JSON.parse(
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

const dayElements = document.querySelectorAll(".day-of-week");
const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const weekName = document.getElementById("weekName");
const weekSpace = document.getElementById("week-space");
let currentIndex = -1;

function renderCalendarWeek() {
  if (currentIndex < 0 || !weeks.length) {
    weekName.textContent = "Chưa có dữ liệu tuần học";
    weekSpace.textContent = "";
    previousWeek.disabled = true;
    nextWeek.disabled = true;
    dayElements.forEach((element) => {
      element.textContent = "";
    });
    renderAssignments();
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
  renderAssignments();
}

function renderAssignments() {
  const cells = new Map();
  document.querySelectorAll(".schedule-cell").forEach((cell) => {
    cell.replaceChildren();
    cells.set(`${cell.dataset.day}:${cell.dataset.session}`, cell);
  });

  if (currentIndex < 0 || !weeks.length) return;

  const weekId = Number(weeks[currentIndex].id);
  assignments.forEach((assignment) => {
    if (Number(assignment.MaTuanHoc) !== weekId) return;

    const day = Number(assignment.Thu) - 2;
    const session = Number(assignment.BuoiThucHanh);
    if (day < 0 || day > 6 || session < 1 || session > 3) return;

    const cell = cells.get(`${day}:${session}`);
    if (!cell) return;

    const card = document.createElement("div");
    card.className = "scheduled-item";
    card.textContent = `Phòng ${assignment.TenPhong}`;
    cell.appendChild(card);
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
  }
});

nextWeek.addEventListener("click", () => {
  if (currentIndex < weeks.length - 1) {
    currentIndex += 1;
    renderCalendarWeek();
  }
});

renderCalendarWeek();
