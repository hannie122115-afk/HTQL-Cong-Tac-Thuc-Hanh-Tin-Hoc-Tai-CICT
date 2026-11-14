const reportModal = document.getElementById("computer-report");
const closeReportButton = document.getElementById("close-report");

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

document.querySelectorAll(".report-detail-act").forEach((button) => {
  button.addEventListener("click", () => {
    markReportAsRead(button);

    const computerId = (button.dataset.computerId || "").trim();
    const isComputerReport = computerId !== "";

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

    reportModal.classList.add("show");
    reportModal.setAttribute("aria-hidden", "false");
    closeReportButton.focus();
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
