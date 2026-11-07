const weeksElement = document.getElementById("weeks-data");
const scheduledElement = document.getElementById("scheduled-data");
const weeks = weeksElement ? JSON.parse(weeksElement.textContent) : [];
const scheduledRequests = scheduledElement
  ? JSON.parse(scheduledElement.textContent)
  : [];

const sessionButtons = document.querySelectorAll(".session-btn");
const dayElements = document.querySelectorAll(".day-of-week");
const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const weekName = document.getElementById("weekName");
const weekSpace = document.getElementById("week-space");

if (previousWeek && nextWeek && weekName && weekSpace) {
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

  // xac dinh lich thuoc thu nao
  function getOccurrences(schedule, week) {
    const occurrences = new Map();
    if (
      schedule.MaTuanHoc &&
      Number(schedule.MaTuanHoc) !== Number(week.id)
    ) {
      return occurrences;
    }
    const dates = (schedule.DanhSachNgay || "").split(",").filter(Boolean);

    dates.forEach((date) => {
      if (date >= week.start && date <= week.end) {
        occurrences.set(date, getDayIndex(date));
      }
    });

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
          if (day >= 0 && day < 7) {
            occurrences.set(`recurring-${day}`, day);
          }
        });
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
  if (currentWeekIndex < 0 && weeks.length > 0) currentWeekIndex = 0;

  const savedSession = sessionStorage.getItem("publicCalendarSession");
  let currentSession = ["1", "2", "3"].includes(savedSession)
    ? savedSession
    : "1";

  function renderWeek() {
    if (currentWeekIndex < 0 || weeks.length === 0) {
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
    document.querySelectorAll(".session-row").forEach((row) => {
      row.toggleAttribute("hidden", row.dataset.session !== currentSession);
    });

    document.querySelectorAll(".schedule-cell").forEach((cell) => {
      cell.replaceChildren(); // xoa nd ben tỏng khi chuyen tuan
    });

    if (currentWeekIndex < 0 || weeks.length === 0) return;

    const week = weeks[currentWeekIndex];
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
        course.textContent = `${schedule.TenHocPhan}`;
        card.appendChild(course);

        const group = document.createElement("div");
        group.className = "scheduled-item-group";
        if (schedule.NhomHocPhan) {
          group.textContent = `Nhóm: ${schedule.NhomHocPhan}`;
        }
        card.appendChild(group);

        const teacher = document.createElement("div");
        teacher.className = "scheduled-item-teacher";
        teacher.textContent = `Giảng viên: ${schedule.TenGiangVien || "Chưa cập nhật"}`;
        card.appendChild(teacher);

        cell.appendChild(card);
      });
    });
  }

  function selectSession(session) {
    currentSession = session;
    sessionStorage.setItem("publicCalendarSession", session);
    sessionButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.session === session);
    });
    renderCalendar();
  }

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
}
