const reportModal = document.getElementById("computer-report");
const reportForm = document.getElementById("report-status-form");
const statusSelect = document.getElementById("report-status");
const closeReportButton = document.getElementById("close-report");
const successPopup = document.getElementById("popup-success");

const machineStatuses = [
  { value: 0, label: "Hư hỏng" },
  { value: 1, label: "Đang hoạt động" },
  { value: 2, label: "Đang sửa chữa" },
  { value: 3, label: "Đang bảo trì" },
];

const roomStatuses = [
  { value: -1, label: "Ngừng hoạt động" },
  { value: 1, label: "Đang hoạt động" },
  { value: 0, label: "Bảo trì" },
];

function closeReport() {
  reportModal.classList.remove("show");
  reportModal.setAttribute("aria-hidden", "true");
}

function markReportAsRead(button) {
  if (button.dataset.read === "true") {
    return;
  }

  fetch(`/admin/report/${button.dataset.reportId}/read`, { method: "POST" })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Could not mark report as read (${response.status}).`);
      }

      button.dataset.read = "true";
      button.closest("tr").classList.remove("is-unread");
      button.closest("tr").classList.add("is-read");
    })
    .catch((error) => {
      console.error("Unable to save report read state:", error);
    });
}

if (successPopup.dataset.show === "true") {
  successPopup.classList.add("show");
  window.setTimeout(() => successPopup.classList.remove("show"), 300);
}

document.querySelectorAll(".report-detail-act").forEach((button) => {
  button.addEventListener("click", () => {
    markReportAsRead(button);

    const computerId = button.dataset.computerId;
    const isComputerReport = computerId !== "";
    const statuses = isComputerReport ? machineStatuses : roomStatuses;

    button.classList.add("is-viewed");

    document.getElementById("report-type").textContent = isComputerReport
      ? "Tình trạng máy tính"
      : "Tình trạng phòng";
    document.getElementById("report-title").textContent = isComputerReport
      ? "Báo cáo tình trạng máy tính"
      : "Báo cáo tình trạng phòng";
    document.getElementById("report-code").textContent =
      `BC${button.dataset.reportId}`;
    document.getElementById("report-room-id").textContent =
      button.dataset.roomId;
    document.getElementById("report-computer-item").hidden =
      !isComputerReport;
    document.getElementById("report-computer-id").textContent = computerId;
    document.getElementById("report-description").textContent =
      button.dataset.description;
    document.getElementById("report-reporter").textContent =
      button.dataset.reporter;

    statusSelect.replaceChildren(
      ...statuses.map((status) => {
        const option = document.createElement("option");
        option.value = status.value;
        option.textContent = status.label;
        return option;
      }),
    );
    statusSelect.value = button.dataset.currentStatus;
    reportForm.action = `/admin/report/${button.dataset.reportId}/status`;

    reportModal.classList.add("show");
    reportModal.setAttribute("aria-hidden", "false");
    statusSelect.focus();
  });
});

closeReportButton.addEventListener("click", closeReport);

reportModal.addEventListener("click", (event) => {
  if (event.target === reportModal) {
    closeReport();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && reportModal.classList.contains("show")) {
    closeReport();
  }
});
