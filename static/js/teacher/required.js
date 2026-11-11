let searchTimeout;

function updateMinPracticeDate() {
  const practiceDayInput = document.querySelector(
    'input[name="required_practice_day"]',
  );
  if (!practiceDayInput) return;

  const minDate = new Date();
  minDate.setDate(minDate.getDate() + 3);

  const year = minDate.getFullYear();
  const month = String(minDate.getMonth() + 1).padStart(2, "0");
  const day = String(minDate.getDate()).padStart(2, "0");

  practiceDayInput.min = `${year}-${month}-${day}`;
}

updateMinPracticeDate();

// ==========================add required=================

// AN HIEN ADD REQUIRED
const addBtn = document.getElementById("required-add-act");
const addContainer = document.getElementById("required-add-container");
const cancelBtn = document.getElementById("cancel-add-required-btn");
const requiredForm = document.getElementById("required-form");
const semesterSelect = document.getElementById("required-semester");
const groupSelect = document.getElementById("required_group_id");
const courseSoftware = document.getElementById("required-course-software");

addBtn.addEventListener("click", function () {
  if (
    addContainer.classList.contains("active") ||
    addContainer.style.display === "block"
  ) {
    addContainer.classList.remove("active");
    addContainer.style.display = "none";
  } else {
    addContainer.classList.add("active");
    addContainer.style.display = "block";
    const firstInput = document.getElementById("required_course_name");
    if (firstInput) firstInput.focus();
  }
});

cancelBtn.addEventListener("click", function () {
  addContainer.classList.remove("active");
  addContainer.style.display = "none";
  if (requiredForm) {
    requiredForm.reset();
    resetCourseDetails();
  }
});

// COURSES

const courseInput = document.getElementById("required_course_name");
const courseIdInput = document.getElementById("required_course_id");
const suggestionCourseBox = document.getElementById("course-suggestions");

function resetCourseDetails() {
  groupSelect.replaceChildren(new Option("Chọn học phần trước", ""));
  groupSelect.disabled = true;
  courseSoftware.textContent = "Chọn học phần để xem phần mềm.";
}

async function loadCourseDetails(courseId) {
  const semesterId = semesterSelect.value;
  if (!courseId || !semesterId) {
    resetCourseDetails();
    return;
  }

  groupSelect.replaceChildren(new Option("Đang tải nhóm học phần...", ""));
  groupSelect.disabled = true;
  courseSoftware.textContent = "Đang tải phần mềm tương thích...";

  try {
    const params = new URLSearchParams({
      course_id: courseId,
      semester_id: semesterId,
    });
    const [groupsResponse, softwareResponse] = await Promise.all([
      fetch(`/api/course-groups?${params}`),
      fetch(`/api/course-software?${params}`),
    ]);
    if (!groupsResponse.ok || !softwareResponse.ok) {
      throw new Error("Không tải được nhóm học phần hoặc phần mềm.");
    }

    const [groups, programs] = await Promise.all([
      groupsResponse.json(),
      softwareResponse.json(),
    ]);
    if (
      courseIdInput.value !== String(courseId) ||
      semesterSelect.value !== semesterId
    ) {
      return;
    }

    groupSelect.replaceChildren(new Option("Chọn nhóm học phần", ""));
    groups.forEach((group) => {
      groupSelect.appendChild(new Option(group.TenNhom, group.MaNhom));
    });
    groupSelect.disabled = groups.length === 0;
    if (groups.length === 0) {
      groupSelect.replaceChildren(
        new Option("Không có nhóm trong học kỳ này", ""),
      );
    }
    courseSoftware.textContent = programs.length
      ? programs.map((program) => program.TenPhanMem).join(", ")
      : "Học phần chưa có phần mềm tương thích.";
  } catch (error) {
    console.error(error);
    resetCourseDetails();
    showRequiredError(
      "Không tải được nhóm học phần và phần mềm tương thích.",
      groupSelect,
    );
  }
}

semesterSelect.addEventListener("change", function () {
  courseInput.value = "";
  courseIdInput.value = "";
  suggestionCourseBox.replaceChildren();
  resetCourseDetails();
  weekStartInput.value = "";
  weekStartIdInput.value = "";
  weekEndInput.value = "";
  weekEndIdInput.value = "";
  weekStartDate.textContent = "";
  weekEndDate.textContent = "";
});

courseInput.addEventListener("input", function () {
  const keyword = this.value.trim();

  courseIdInput.value = "";
  resetCourseDetails();
  clearTimeout(searchTimeout);
  suggestionCourseBox.replaceChildren();
  if (keyword.length === 0 || !semesterSelect.value) {
    return;
  }

  searchTimeout = setTimeout(async function () {
    try {
      const semesterId = semesterSelect.value;
      const response = await fetch(
        `/api/courses?keyword=${encodeURIComponent(keyword)}&semester_id=${encodeURIComponent(semesterId)}`,
      );
      if (!response.ok) {
        throw new Error("Không thể tìm học phần");
      }
      const courses = await response.json();
      if (
        courseInput.value.trim() !== keyword ||
        semesterSelect.value !== semesterId
      ) {
        return;
      }
      suggestionCourseBox.replaceChildren();

      courses.forEach(function (course) {
        const item = document.createElement("div");
        item.className = "course-suggestion-item";
        item.textContent = `${course.MaHocPhan} - ${course.TenHocPhan}`;

        item.addEventListener("click", function () {
          courseInput.value = course.TenHocPhan;
          courseIdInput.value = course.MaHocPhan;
          suggestionCourseBox.replaceChildren();
          loadCourseDetails(course.MaHocPhan);
        });
        suggestionCourseBox.appendChild(item);
      });

      if (courses.length === 0) {
        const empty = document.createElement("div");
        empty.className = "course-suggestion-empty";
        empty.textContent = "Không tìm thấy học phần";
        suggestionCourseBox.appendChild(empty);
      }
    } catch (error) {
      console.error(error);
      suggestionCourseBox.replaceChildren();
    }
  }, 300);
});
document.addEventListener("click", function (event) {
  if (!event.target.closest(".required-add-item")) {
    suggestionCourseBox.replaceChildren();
  }
});

// WEEKS

const weekStartInput = document.getElementById("required-week-start");
const weekStartIdInput = document.getElementById("required-week-start-id");
const suggestionWeekStartBox = document.getElementById(
  "week-start-suggestions",
);
const weekStartDate = document.getElementById("week-start-date");

const weekEndInput = document.getElementById("required-week-end");
const weekEndIdInput = document.getElementById("required-week-end-id");
const suggestionWeekEndBox = document.getElementById("week-end-suggestions");
const weekEndDate = document.getElementById("week-end-date");

function setupWeekAutocomplete(input, idInput, suggestionBox, dateSpan) {
  let searchTimeout;
  input.addEventListener("input", function () {
    const keyword = this.value.trim();
    idInput.value = "";
    dateSpan.textContent = "";
    dateSpan.classList.remove("field-error");
    input.removeAttribute("aria-invalid");

    clearTimeout(searchTimeout);
    suggestionBox.replaceChildren();

    if (!keyword || !semesterSelect.value) return;
    searchTimeout = setTimeout(async function () {
      try {
        const semesterId = semesterSelect.value;
        const response = await fetch(
          `/api/weeks?keyword=${encodeURIComponent(keyword)}&semester_id=${encodeURIComponent(semesterId)}`,
        );
        if (!response.ok) {
          throw new Error("Không thể tìm tuần học");
        }

        const weeks = await response.json();
        if (
          input.value.trim() !== keyword ||
          semesterSelect.value !== semesterId
        ) {
          return;
        }
        suggestionBox.replaceChildren();

        weeks.forEach(function (week) {
          const item = document.createElement("div");
          item.className = "week-suggestion-item";

          item.textContent = `Tuần ${week.TenTuanHoc}`;

          item.addEventListener("click", function () {
            input.value = `Tuần ${week.TenTuanHoc}`;
            idInput.value = week.MaTuanHoc;

            const [day, month, year] = week.NgayBatDau.split("/");
            const startDate = new Date(year, month - 1, day);
            const [daye, monthe, yeare] = week.NgayKetThuc.split("/");
            const startEnd = new Date(yeare, monthe - 1, daye);
            startDate.setHours(0, 0, 0, 0);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            if (
              (startDate <= today && startEnd >= today) ||
              (startDate > today && startEnd > today)
            ) {
              dateSpan.classList.remove("field-error");
              input.removeAttribute("aria-invalid");
              dateSpan.textContent = `Từ ngày ${week.NgayBatDau} đến ngày ${week.NgayKetThuc}.`;
            } else {
              dateSpan.classList.add("field-error");
              dateSpan.setAttribute("role", "alert");
              input.setAttribute("aria-invalid", "true");
              dateSpan.textContent =
                "Không cho phép yêu cầu từ tuần ở quá khứ!";
            }

            suggestionBox.replaceChildren();
          });
          suggestionBox.appendChild(item);
        });

        if (weeks.length === 0) {
          const empty = document.createElement("div");
          empty.className = "week-suggestion-empty";
          empty.textContent = "Không tìm thấy tuần học";
          suggestionBox.appendChild(empty);
        }
      } catch (error) {
        console.error(error);
        suggestionBox.replaceChildren();
      }
    }, 300);
  });
}

setupWeekAutocomplete(
  weekStartInput,
  weekStartIdInput,
  suggestionWeekStartBox,
  weekStartDate,
);

setupWeekAutocomplete(
  weekEndInput,
  weekEndIdInput,
  suggestionWeekEndBox,
  weekEndDate,
);

document.addEventListener("click", function (event) {
  if (!event.target.closest(".required-add-item-box-input")) {
    suggestionWeekStartBox.replaceChildren();
    suggestionWeekEndBox.replaceChildren();
  }
});

// AN HIEN REQUIRED-TYPE
const requiredTypeRadios = document.querySelectorAll(
  'input[name="required_type"]',
);
const weekStartField = document.getElementById("week-start-field");
const weekEndField = document.getElementById("week-end-field");
const practiceDayField = document.getElementById("practice-day-field");
const weekDayField = document.getElementById("week-day-field");

weekStartField.hidden = false;
weekEndField.hidden = false;
practiceDayField.hidden = true;
weekDayField.hidden = false;

requiredTypeRadios.forEach((radio) => {
  radio.addEventListener("change", function () {
    if (this.value === "thuc_hanh") {
      weekStartField.hidden = false;
      weekEndField.hidden = false;
      weekDayField.hidden = false;
      practiceDayField.hidden = true;
    } else {
      weekStartField.hidden = true;
      weekEndField.hidden = true;
      weekDayField.hidden = true;
      practiceDayField.hidden = false;
    }
  });
});

// POPUP ERROR
const popupError = document.getElementById("popup-error");
const popupErrorClose = document.getElementById("popup-error-close");
const popupErrorMessage = document.getElementById("popup-error-message");
const practiceDayInput = document.getElementById("required_practice_day");
let inputToFocus = null;

function showRequiredError(message, target) {
  popupErrorMessage.textContent = message;
  inputToFocus = target;
  popupError.classList.add("show");
}

function getErrorFocusTarget(message) {
  if (message.includes("học kỳ")) return semesterSelect;
  if (message.includes("nhóm học phần")) return groupSelect;
  if (message.includes("học phần")) return courseInput;
  if (message.includes("buổi thực hành")) {
    return document.querySelector('input[name="required_lesson"]');
  }
  if (message.includes("thứ thực hành")) {
    return document.querySelector('input[name="required_week_day"]');
  }
  if (message.includes("ngày thực hành")) return practiceDayInput;
  if (message.includes("tuần") && message.includes("kết thúc")) {
    return weekEndInput;
  }
  if (message.includes("tuần")) return weekStartInput;
  if (message.includes("loại yêu cầu")) {
    return document.querySelector('input[name="required_type"]');
  }
  return null;
}

if (popupErrorMessage.textContent.trim()) {
  inputToFocus = getErrorFocusTarget(popupErrorMessage.textContent);
  popupError.classList.add("show");
}

// Đóng popup error
popupErrorClose.addEventListener("click", function () {
  popupError.classList.remove("show");
  if (inputToFocus) {
    inputToFocus.focus();
    inputToFocus = null;
  }
});

// POPUP SUCCESS

const requiredPage = document.getElementById("required-page");
const popupSuccess = document.getElementById("popup-success");

if (requiredPage && popupSuccess) {
  if (requiredPage.dataset.success) {
    popupSuccess.classList.add("show");
    setTimeout(() => {
      window.location.reload();
    }, 300);
  }
}

// CHECK NULL REQUIRED FORM
requiredForm.addEventListener("submit", function (e) {
  if (!courseInput.value.trim() || !courseIdInput.value) {
    e.preventDefault();
    showRequiredError(
      "Vui lòng chọn Học phần từ danh sách gợi ý!",
      courseInput,
    );
    return;
  }

  if (!semesterSelect.value) {
    e.preventDefault();
    showRequiredError("Vui lòng chọn học kỳ.", semesterSelect);
    return;
  }

  if (!groupSelect.value) {
    e.preventDefault();
    showRequiredError("Vui lòng chọn nhóm học phần.", groupSelect);
    return;
  }

  const selectedType = document.querySelector(
    'input[name="required_type"]:checked',
  )?.value;

  if (selectedType === "thuc_hanh") {
    const selectedWeekDays = document.querySelectorAll(
      'input[name="required_week_day"]:checked',
    );
    if (selectedWeekDays.length === 0) {
      e.preventDefault();
      showRequiredError(
        "Vui lòng chọn ít nhất một Thứ thực hành trong tuần!",
        document.querySelector('input[name="required_week_day"]'),
      );
      return;
    }

    if (!weekStartInput.value.trim() || !weekStartIdInput.value) {
      e.preventDefault();
      showRequiredError(
        "Vui lòng chọn Tuần bắt đầu từ danh sách gợi ý!",
        weekStartInput,
      );
      return;
    }

    if (!weekEndInput.value.trim() || !weekEndIdInput.value) {
      e.preventDefault();
      showRequiredError(
        "Vui lòng chọn Tuần kết thúc từ danh sách gợi ý!",
        weekEndInput,
      );
      return;
    }

    const startWeekVal = parseInt(weekStartIdInput.value, 10);
    const endWeekVal = parseInt(weekEndIdInput.value, 10);
    if (endWeekVal < startWeekVal) {
      e.preventDefault();
      showRequiredError(
        "Tuần kết thúc phải lớn hơn hoặc bằng tuần bắt đầu!",
        weekEndInput,
      );
      return;
    }
  } else if (selectedType === "khac") {
    const practiceDayInput = document.querySelector(
      'input[name="required_practice_day"]',
    );

    if (!practiceDayInput || !practiceDayInput.value.trim()) {
      e.preventDefault();
      showRequiredError("Vui lòng chọn Ngày thực hành!", practiceDayInput);
      return;
    }
  }
});

// REQUIRED DETAIL
const detailContainer = document.getElementById("required-detail-container");
const closeDetailBtn = document.getElementById("close-detail-btn");

document.querySelectorAll(".see-detail-act").forEach(function (button) {
  button.addEventListener("click", function () {
    const data = button.dataset;

    document.getElementById("detail-id").textContent = `YC${data.id}`;
    document.getElementById("detail-course").textContent =
      `${data.courseId} - ${data.course}`;
    document.getElementById("detail-group").textContent = `${data.group}`;
    document.getElementById("detail-number").textContent =
      `${data.number} sinh viên`;
    document.getElementById("detail-program").textContent = data.program;
    document.getElementById("detail-note").textContent =
      data.note || "Không có";
    document.getElementById("detail-teacher").textContent = data.teacher || "";
    document.getElementById("detail-date").textContent = data.date || "";

    document.getElementById("detail-lesson").textContent = data.lesson || "";

    const statuses = {
      0: '<i class="fa-regular fa-hourglass"></i> Chờ duyệt',
      1: '<i class="fa-solid fa-calendar-day"></i> Chờ xếp lịch',
      2: '<i class="fa-solid fa-circle-check"></i> Đã duyệt',
      3: '<i class="fa-regular fa-circle-xmark"></i> Bị từ chối',
    };
    const detailStatus = document.getElementById("detail-status");
    detailStatus.innerHTML = statuses[data.status] || "";
    detailStatus.className = `required-detail-status status-${
      { 0: "warning", 1: "info", 2: "success", 3: "danger" }[data.status] ||
      "muted"
    }`;

    const weekDayBox = document.getElementById("detail-week-day-box");
    const weekStartBox = document.getElementById("detail-week-start-box");
    const weekEndBox = document.getElementById("detail-week-end-box");
    const practiceDayBox = document.getElementById("detail-practice-day-box");

    if (data.type === "thuc_hanh") {
      document.getElementById("detail-type").textContent = "Thực hành";

      let formattedThu = "";
      if (data.thu) {
        formattedThu = data.thu
          .split(", ")
          .map((t) => (t === "8" ? "Chủ nhật" : `Thứ ${t}`))
          .join(", ");
      }
      document.getElementById("detail-week-day").textContent = formattedThu;
      document.getElementById("detail-week-start").textContent =
        `Tuần ${data.tuanBd}`;
      document.getElementById("detail-week-end").textContent =
        `Tuần ${data.tuanKt}`;

      weekDayBox.style.display = "flex";
      weekStartBox.style.display = "flex";
      weekEndBox.style.display = "flex";
      practiceDayBox.style.display = "none";
    } else {
      document.getElementById("detail-type").textContent = "Khác";
      document.getElementById("detail-practice-day").textContent = data.ngayTh;

      weekDayBox.style.display = "none";
      weekStartBox.style.display = "none";
      weekEndBox.style.display = "none";
      practiceDayBox.style.display = "flex";
    }

    detailContainer.classList.add("show");
  });
});

if (closeDetailBtn && detailContainer) {
  closeDetailBtn.addEventListener("click", function () {
    detailContainer.classList.remove("show");
  });
}

// DELETE REQUIRED POPUP
const deleteRequiredPopup = document.getElementById("popup-delete-required");
const deleteRequiredCourse = document.getElementById("delete-required-course");
const deleteRequiredForm = document.getElementById("delete-required-form");
const deleteRequiredCancel = document.getElementById("delete-required-cancel");

document.querySelectorAll(".delete-detail-act").forEach(function (button) {
  button.addEventListener("click", function () {
    const id = button.dataset.id;
    const course = button.dataset.course;

    if (deleteRequiredCourse) {
      deleteRequiredCourse.textContent = course;
    }

    if (deleteRequiredForm) {
      deleteRequiredForm.action = `/teacher/required/${id}/delete`;
    }

    if (deleteRequiredPopup) {
      deleteRequiredPopup.classList.add("show");
    }
  });
});

if (deleteRequiredCancel && deleteRequiredPopup) {
  deleteRequiredCancel.addEventListener("click", function () {
    deleteRequiredPopup.classList.remove("show");
  });
}
