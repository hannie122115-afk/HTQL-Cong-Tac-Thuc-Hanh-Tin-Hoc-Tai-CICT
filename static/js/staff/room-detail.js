const reportModal = document.getElementById("computer-report");
const reportForm = document.getElementById("computer-report-form");
const computerIdInput = document.getElementById("computer-id");
const computerName = document.getElementById("report-computer-name");
const cancelReportButton = document.getElementById("cancel-computer-report");
const cancelConfirmation = document.getElementById("popup-cancel-confirm");
const cancelNoButton = document.getElementById("popup-cancel-no");
const cancelYesButton = document.getElementById("popup-cancel-yes");
const errorPopup = document.getElementById("popup-error");
const errorMessage = document.getElementById("popup-error-message");
const errorCloseButton = document.getElementById("popup-error-close");
const statusField = reportForm.querySelector("[name='current_status']");

reportForm.addEventListener("submit", (event) => {
  if (!statusField.value.trim()) {
    event.preventDefault();
    errorMessage.textContent =
      "Vui lòng nhập tình trạng cụ thể trước khi gửi báo cáo.";
    errorPopup.classList.add("show");
  }
});

errorCloseButton.addEventListener("click", () => {
  errorPopup.classList.remove("show");
  statusField.focus();
});

document.querySelectorAll(".update-computer-btn").forEach((button) => {
  button.addEventListener("click", () => {
    computerIdInput.value = button.dataset.id;
    computerName.textContent = button.dataset.id;
    reportModal.classList.add("show");
    statusField.focus();
  });
});

cancelReportButton.addEventListener("click", () => {
  cancelConfirmation.classList.add("show");
});

cancelNoButton.addEventListener("click", () => {
  cancelConfirmation.classList.remove("show");
});

cancelYesButton.addEventListener("click", () => {
  cancelConfirmation.classList.remove("show");
  reportModal.classList.remove("show");
  reportForm.reset();
  computerName.textContent = "";
});