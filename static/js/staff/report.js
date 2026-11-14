const reportModal = document.getElementById("computer-report");
const closeReportButton = document.getElementById("close-report");

function closeReport() {
  reportModal.classList.remove("show");
  reportModal.setAttribute("aria-hidden", "true");
}

document.querySelectorAll(".report-detail-act").forEach((button) => {
  button.addEventListener("click", () => {
    const computerId = (button.dataset.computerId || "").trim();
    const isComputerReport = computerId !== "";
    // NOTE: Báo cáo của staff không đánh dấu hoặc đổi màu sau khi xem.
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
    document.getElementById("report-computer-item").hidden = !isComputerReport;
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
  if (event.target === reportModal) closeReport();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && reportModal.classList.contains("show"))
    closeReport();
});
