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
  }
});

// COURSES

const courseInput = document.getElementById("required_course_name");
const courseIdInput = document.getElementById("required_course_id");
const suggestionCourseBox = document.getElementById("course-suggestions");

courseInput.addEventListener("input", function () {
  const keyword = this.value.trim();

  // Xóa mã đã chọn nếu người dùng sửa nội dung
  courseIdInput.value = "";
  clearTimeout(searchTimeout);
  suggestionCourseBox.replaceChildren();
  if (keyword.length === 0) {
    return;
  }

  searchTimeout = setTimeout(async function () {
    try {
      const response = await fetch(
        `/api/courses?keyword=${encodeURIComponent(keyword)}`,
      );
      if (!response.ok) {
        throw new Error("Không thể tìm học phần");
      }
      const courses = await response.json();
      suggestionCourseBox.replaceChildren();

      courses.forEach(function (course) {
        const item = document.createElement("div");
        item.className = "course-suggestion-item";
        item.textContent = `${course.MaHocPhan} - ${course.TenHocPhan}`;

        item.addEventListener("click", function () {
          courseInput.value = course.TenHocPhan;
          courseIdInput.value = course.MaHocPhan;
          suggestionCourseBox.replaceChildren();
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

//PROGRAMS

const programInput = document.getElementById("required_program_name");
const programIdInput = document.getElementById("required_program_id");
const suggestionProgramBox = document.getElementById("program-suggestions");

programInput.addEventListener("input", function () {
  const keyword = this.value.trim();

  programIdInput.value = "";
  clearTimeout(searchTimeout);
  suggestionProgramBox.replaceChildren();
  if (keyword.length === 0) {
    return;
  }

  searchTimeout = setTimeout(async function () {
    try {
      const response = await fetch(
        `/api/programs?keyword=${encodeURIComponent(keyword)}`,
      );
      if (!response.ok) {
        throw new Error("Không thể tìm học phần");
      }
      const programs = await response.json();
      suggestionProgramBox.replaceChildren();

      programs.forEach(function (program) {
        const item = document.createElement("div");
        item.className = "program-suggestion-item";
        item.textContent = `${program.MaPhanMem} - ${program.TenPhanMem}`;

        item.addEventListener("click", function () {
          programInput.value = program.TenPhanMem;
          programIdInput.value = program.MaPhanMem;
          suggestionProgramBox.replaceChildren();
        });
        suggestionProgramBox.appendChild(item);
      });

      if (programs.length === 0) {
        const empty = document.createElement("div");
        empty.className = "program-suggestion-empty";
        empty.textContent = "Không tìm thấy phần mềm";
        suggestionProgramBox.appendChild(empty);
      }
    } catch (error) {
      console.error(error);
      suggestionProgramBox.replaceChildren();
    }
  }, 300);
});
document.addEventListener("click", function (event) {
  if (!event.target.closest(".required-add-item")) {
    suggestionProgramBox.replaceChildren();
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

    clearTimeout(searchTimeout);
    suggestionBox.replaceChildren();

    if (!keyword) return;
    searchTimeout = setTimeout(async function () {
      try {
        const response = await fetch(
          `/api/weeks?keyword=${encodeURIComponent(keyword)}`,
        );
        if (!response.ok) {
          throw new Error("Không thể tìm tuần học");
        }

        const weeks = await response.json();
        if (input.value.trim() !== keyword) return;
        suggestionBox.replaceChildren();

        weeks.forEach(function (week) {
          const item = document.createElement("div");
          item.className = "week-suggestion-item";

          item.textContent = `Tuần ${week.TenTuanHoc}`;

          item.addEventListener("click", function () {
            input.value = `Tuần ${week.TenTuanHoc}`;
            idInput.value = week.MaTuanHoc;
            dateSpan.textContent = `Từ ngày ${week.NgayBatDau} đến ngày ${week.NgayKetThuc}.`;
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
    if (this.value === "1") {
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

let inputToFocus = null;

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
const popupSuccessClose = document.getElementById("popup-success-close");

if (requiredPage && popupSuccess && popupSuccessClose) {
  if (requiredPage.dataset.success) {
    popupSuccess.classList.add("show");
  }

  popupSuccessClose.addEventListener("click", function () {
    popupSuccess.classList.remove("show");
  });
}

// CHECK NULL REQUIRED FORM
requiredForm.addEventListener("submit", function (e) {
  if (!courseInput.value.trim() || !courseIdInput.value) {
    e.preventDefault();
    popupErrorMessage.textContent =
      "Vui lòng chọn Học phần từ danh sách gợi ý!";
    popupError.classList.add("show");
    inputToFocus = courseInput;
    return;
  }

  if (!programInput.value.trim() || !programIdInput.value) {
    e.preventDefault();
    popupErrorMessage.textContent =
      "Vui lòng chọn Phần mềm từ danh sách gợi ý!";
    popupError.classList.add("show");
    inputToFocus = programInput;
    return;
  }

  const computerAmountInput = document.querySelector(
    'input[name="required_computer_amount"]',
  );
  if (!computerAmountInput.value || parseInt(computerAmountInput.value) <= 0) {
    e.preventDefault();
    popupErrorMessage.textContent =
      "Vui lòng nhập Số lượng máy tính hợp lệ (lớn hơn 0 và nhỏ hơn 60)!";
    popupError.classList.add("show");
    inputToFocus = computerAmountInput;
    return;
  }

  const selectedType = document.querySelector(
    'input[name="required_type"]:checked',
  )?.value;

  if (selectedType === "1") {
    const selectedWeekDays = document.querySelectorAll(
      'input[name="required-week-day"]:checked',
    );
    if (selectedWeekDays.length === 0) {
      e.preventDefault();
      popupErrorMessage.textContent =
        "Vui lòng chọn ít nhất một Thứ thực hành trong tuần!";
      popupError.classList.add("show");
      return;
    }

    if (!weekStartInput.value.trim() || !weekStartIdInput.value) {
      e.preventDefault();
      popupErrorMessage.textContent =
        "Vui lòng chọn Tuần bắt đầu từ danh sách gợi ý!";
      popupError.classList.add("show");
      inputToFocus = weekStartInput;
      return;
    }

    if (!weekEndInput.value.trim() || !weekEndIdInput.value) {
      e.preventDefault();
      popupErrorMessage.textContent =
        "Vui lòng chọn Tuần kết thúc từ danh sách gợi ý!";
      popupError.classList.add("show");
      inputToFocus = weekEndInput;
      return;
    }

    const startWeekVal = parseInt(weekStartIdInput.value, 10);
    const endWeekVal = parseInt(weekEndIdInput.value, 10);
    if (endWeekVal < startWeekVal) {
      e.preventDefault();
      popupErrorMessage.textContent =
        "Tuần kết thúc phải lớn hơn hoặc bằng tuần bắt đầu!";
      popupError.classList.add("show");
      inputToFocus = weekEndInput;
      return;
    }
  } else if (selectedType === "0") {
    const practiceDayInput = document.querySelector(
      'input[name="required_practice_day"]',
    );

    if (!practiceDayInput || !practiceDayInput.value.trim()) {
      e.preventDefault();
      popupErrorMessage.textContent = "Vui lòng chọn Ngày thực hành!";
      popupError.classList.add("show");
      inputToFocus = practiceDayInput;
      return;
    }
  }
});
