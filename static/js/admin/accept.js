const detailContainer = document.getElementById("required-detail-container");
const closeDetailBtn = document.getElementById("close-detail-btn");
const acceptDetailBtn = document.getElementById("accept-detail-btn");
const refuseDetailBtn = document.getElementById("refuse-detail-btn");

document.querySelectorAll(".see-detail-act").forEach(function (button) {
  button.addEventListener("click", function () {
    const data = button.dataset;
    currentRequiredId = data.id;

    document.getElementById("detail-id").textContent = `YC${data.id}`;
    document.getElementById("detail-course").textContent =
      `${data.courseId} - ${data.course}`;
    document.getElementById("detail-program").textContent = data.program;
    document.getElementById("detail-amount").textContent = `${data.amount} máy`;
    document.getElementById("detail-note").textContent =
      data.note || "Không có";
    document.getElementById("detail-teacher").textContent = data.teacher || "";
    document.getElementById("detail-date").textContent = data.date || "";

    const lessons = {
      1: "Sáng (7h00 - 11h30)",
      2: "Chiều (13h30 - 17h00)",
      3: "Tối (18h20 - 20h00)",
    };
    document.getElementById("detail-lesson").textContent =
      lessons[data.lesson] || "";

    const statuses = {
      0: '<i class="fa-regular fa-hourglass"></i> Chờ duyệt',
      1: '<i class="fa-solid fa-calendar-day"></i> Chờ xếp lịch',
      2: '<i class="fa-solid fa-circle-check"></i> Đã duyệt',
      3: '<i class="fa-regular fa-circle-xmark"></i> Bị từ chối',
    };
    document.getElementById("detail-status").innerHTML =
      statuses[data.status] || "";

    const weekDayBox = document.getElementById("detail-week-day-box");
    const weekStartBox = document.getElementById("detail-week-start-box");
    const weekEndBox = document.getElementById("detail-week-end-box");
    const practiceDayBox = document.getElementById("detail-practice-day-box");

    if (String(data.type) === "1") {
      document.getElementById("detail-type").textContent = "Dài hạn";

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
      document.getElementById("detail-type").textContent = "Phát sinh";
      document.getElementById("detail-practice-day").textContent = data.ngayTh;

      weekDayBox.style.display = "none";
      weekStartBox.style.display = "none";
      weekEndBox.style.display = "none";
      practiceDayBox.style.display = "flex";
    }

    acceptDetailBtn.style.display =
      String(data.status) === "0" ? "block" : "none";

    refuseDetailBtn.style.display =
      String(data.status) === "0" ? "block" : "none";

    detailContainer.classList.add("show");
  });
});

if (closeDetailBtn && detailContainer) {
  closeDetailBtn.addEventListener("click", function () {
    detailContainer.classList.remove("show");
  });
}

// POPUP SUCCESS
const popupSuccess = document.getElementById("popup-success");
const popupSuccessMessage = document.getElementById("popup-success-message");
const popupSuccessClose = document.getElementById("popup-success-close");

function showSuccessPopup(message) {
  if (popupSuccess && popupSuccessMessage) {
    popupSuccessMessage.textContent = message;
    popupSuccess.classList.add("show");
  }
}

if (popupSuccess && popupSuccessClose) {
  popupSuccessClose.addEventListener("click", function () {
    popupSuccess.classList.remove("show");
  });
}

// ACCEPT REQUIRED

let currentRequiredId = null;
acceptDetailBtn.addEventListener("click", async function () {
  if (!currentRequiredId) {
    alert("Không xác định được mã yêu cầu.");
    return;
  }

  try {
    acceptDetailBtn.style.pointerEvents = "none"; //k cho click chuot

    const response = await fetch(`/admin/accept/${currentRequiredId}/accept`, {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      messageError.textContent = result.message || "Không thể duyệt yêu cầu.";
      return;
    }

    showSuccessPopup(result.message);
    setTimeout(() => {
      window.location.reload();
    }, 300);
  } catch (error) {
    console.error("Lỗi duyệt yêu cầu:", error);
    alert("Không thể kết nối đến máy chủ.");
  } finally {
    acceptDetailBtn.style.pointerEvents = "";
  }
});

// REFUSE REQUIRED
const popupRefuse = document.getElementById("popup-refuse-required");
const refuseRequiredForm = document.getElementById("refuse-required-form");
const refuseReason = document.getElementById("refuse-reason");
const messageError = document.getElementById("message-error");
const refuseRequiredCancel = document.getElementById("refuse-required-cancel");

refuseDetailBtn.addEventListener("click", function () {
  popupRefuse.classList.add("show");
});

refuseReason.addEventListener("input", function () {
  messageError.textContent = "";
});

refuseRequiredCancel.addEventListener("click", function () {
  popupRefuse.classList.remove("show");
  messageError.textContent = "";
});

refuseRequiredForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  const reason = refuseReason.value.trim();

  if (!reason) {
    messageError.textContent = "Vui lòng nhập lý do từ chối.";
    refuseReason.focus();
    return;
  }

  const refuseButton = document.getElementById("refuse-required-confirm");

  try {
    refuseButton.disabled = true;

    const response = await fetch(`/admin/accept/${currentRequiredId}/refuse`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        reason: reason,
      }),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      messageError.textContent = result.message || "Không thể từ chối yêu cầu.";
      return;
    }

    popupRefuse.classList.remove("show");
    refuseRequiredForm.reset();
    messageError.textContent = "";

    showSuccessPopup(result.message);
    setTimeout(() => {
      window.location.reload();
    }, 300);
  } catch (error) {
    console.error("Lỗi từ chối yêu cầu:", error);
    messageError.textContent = "Không thể kết nối đến máy chủ.";
  } finally {
    refuseButton.disabled = false;
  }
});
