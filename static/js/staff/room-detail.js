const reportModal = document.getElementById("computer-report");
const reportForm = document.getElementById("computer-report-form");
const reportButton = document.getElementById("report-computers-btn");
const selectAll = document.getElementById("report-select-all");
const machineCheckboxes = Array.from(
  reportForm.querySelectorAll("[name='computer_ids']"),
);
const selectedCount = document.getElementById("report-selected-count");
const cancelReportButton = document.getElementById("cancel-computer-report");
const cancelConfirmation = document.getElementById("popup-cancel-confirm");
const cancelNoButton = document.getElementById("popup-cancel-no");
const cancelYesButton = document.getElementById("popup-cancel-yes");
const errorPopup = document.getElementById("popup-error");
const errorMessage = document.getElementById("popup-error-message");
const errorCloseButton = document.getElementById("popup-error-close");
const statusField = reportForm.querySelector("[name='current_status']");
const newStatus = document.getElementById("new-status");
const commonFields = document.getElementById("common-report-fields");
const individualFields = document.getElementById("individual-report-fields");
const detailsInput = document.getElementById("machine-details-json");
const modeInputs = Array.from(
  reportForm.querySelectorAll("[name='report_mode']"),
);
const machineRows = Array.from(
  reportForm.querySelectorAll(".individual-machine-report"),
);
let errorFocus = statusField;

function isIndividualMode() {
  return modeInputs.some(
    (input) => input.checked && input.value === "individual",
  );
}

function updateReportMode() {
  const individual = isIndividualMode();
  const selected = new Set(
    machineCheckboxes
      .filter((input) => input.checked)
      .map((input) => input.value),
  );
  commonFields.hidden = individual;
  individualFields.hidden = !individual;
  statusField.disabled = individual;
  newStatus.disabled = individual;
  statusField.required = !individual;
  newStatus.required = !individual;
  machineRows.forEach((row) => {
    const active = individual && selected.has(row.dataset.machineId);
    row.hidden = !active;
    row.querySelectorAll("select, textarea").forEach((input) => {
      input.disabled = !active;
      input.required = active;
    });
  });
  detailsInput.value = "";
}
modeInputs.forEach((input) =>
  input.addEventListener("change", updateReportMode),
);

// NOTE: Chọn máy ngay trong hộp báo cáo, bao gồm máy ở mọi trang của phòng.
function updateSelection() {
  const count = machineCheckboxes.filter((checkbox) => checkbox.checked).length;
  selectedCount.textContent = `Đã chọn ${count} máy`;
  selectAll.checked = count > 0 && count === machineCheckboxes.length;
  selectAll.indeterminate = count > 0 && count < machineCheckboxes.length;
  updateReportMode();
}

selectAll.addEventListener("change", () => {
  machineCheckboxes.forEach((checkbox) => {
    checkbox.checked = selectAll.checked;
  });
  updateSelection();
});
machineCheckboxes.forEach((checkbox) =>
  checkbox.addEventListener("change", updateSelection),
);

reportForm.addEventListener("submit", (event) => {
  if (!machineCheckboxes.some((checkbox) => checkbox.checked)) {
    event.preventDefault();
    errorMessage.textContent = "Vui lòng chọn ít nhất một máy tính.";
    errorFocus = machineCheckboxes[0];
    errorPopup.classList.add("show");
    return;
  }
  const fail = (message, input) => {
    event.preventDefault();
    errorMessage.textContent = message;
    errorFocus = input;
    errorPopup.classList.add("show");
    input?.focus();
  };
  if (isIndividualMode()) {
    const details = [];
    for (const row of machineRows.filter((row) => !row.hidden)) {
      const description = row.querySelector(".machine-description");
      const status = row.querySelector(".machine-status");
      if (!description.value.trim() || description.value.trim().length > 2000) {
        fail(
          `Vui lòng nhập diễn giải từ 1 đến 2000 ký tự cho máy ${row.dataset.machineId}.`,
          description,
        );
        return;
      }
      if (!["0", "1", "2", "3"].includes(status.value)) {
        fail(
          `Vui lòng chọn trạng thái cho máy ${row.dataset.machineId}.`,
          status,
        );
        return;
      }
      details.push({
        computer_id: row.dataset.machineId,
        description: description.value.trim(),
        status: Number(status.value),
      });
    }
    detailsInput.value = JSON.stringify(details);
  } else if (
    !statusField.value.trim() ||
    statusField.value.trim().length > 2000
  ) {
    fail("Vui lòng nhập tình trạng cụ thể từ 1 đến 2000 ký tự.", statusField);
  } else if (!["0", "1", "2", "3"].includes(newStatus.value)) {
    fail("Vui lòng chọn trạng thái áp dụng cho các máy.", newStatus);
  }
});

errorCloseButton.addEventListener("click", () => {
  errorPopup.classList.remove("show");
  errorFocus?.focus();
});

reportButton.addEventListener("click", () => {
  reportModal.classList.add("show");
  updateSelection();
  (machineCheckboxes[0] || statusField).focus();
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
  updateSelection();
});
updateSelection();
