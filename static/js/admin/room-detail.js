// ==================== EDIT / CANCEL / SAVE ROOM ====================

const editBtn = document.getElementById("room-edit-btn");
const cancelBtn = document.getElementById("room-cancel-btn");
const saveBtn = document.getElementById("room-save-btn");
const roomForm = document.getElementById("room-edit-form");
const roomValues = document.querySelectorAll(".room-value");
const roomInputs = document.querySelectorAll(".room-input");

// Các trường chọn trong form
const configSelect = document.getElementById("config-id");
const staffSelect = document.getElementById("staff-id");
const roomStatusSelect = document.getElementById("room_status");

// EDIT ROOM
editBtn.addEventListener("click", function () {
  roomForm.classList.add("editing");
  editBtn.style.display = "none";
  cancelBtn.style.display = "inline-flex";
  saveBtn.style.display = "inline-flex";

  roomValues.forEach(function (element) {
    element.style.display = "none";
  });

  roomInputs.forEach(function (input) {
    input.style.display = "block";
  });
});

// ==================== CANCEL EDIT ROOM ====================

const popupConfirm = document.getElementById("popup-confirm");
const popupCancelNo = document.getElementById("popup-cancel-no");
const popupCancelYes = document.getElementById("popup-cancel-yes");

if (cancelBtn && popupConfirm) {
  cancelBtn.addEventListener("click", function () {
    popupConfirm.classList.add("show");
  });
}

popupCancelNo.addEventListener("click", function () {
  popupConfirm.classList.remove("show");
});

popupCancelYes.addEventListener("click", function () {
  popupConfirm.classList.remove("show");
  window.location.reload();
});

// ==================== ADD COMPUTER ====================

const addComputerBtn = document.getElementById("room-detail-add-act");
const computerContainer = document.getElementById("computer-container");
const addComputerForm = document.getElementById("add-computer-form");
const cancelAddComputerBtn = document.getElementById("cancel-add-computer");

addComputerBtn.addEventListener("click", function (event) {
  event.preventDefault();
  computerContainer.classList.add("show");
});

cancelAddComputerBtn.addEventListener("click", function () {
  addComputerForm.reset();
  computerContainer.classList.remove("show");
});

// ==================== UPDATE COMPUTER STATUS ====================

const updateComputerBtns = document.querySelectorAll(".update-computer-btn");
const statusOverlay = document.getElementById("computer-status-overlay");
const statusForm = document.getElementById("computer-status-form");
const statusSelect = document.getElementById("computer-status-select");
const cancelStatusBtn = document.getElementById("cancel-computer-status");

updateComputerBtns.forEach(function (btn) {
  btn.addEventListener("click", function () {
    const computerId = this.dataset.id;
    const currentStatus = this.dataset.status;

    statusForm.action = this.closest("tr")
      .querySelector(".room-detail-delete-computer")
      .href.replace(/\/delete$/, "/update");

    statusSelect.value = currentStatus;
    statusOverlay.classList.add("show");
  });
});

cancelStatusBtn.addEventListener("click", function () {
  statusOverlay.classList.remove("show");
  statusForm.reset();
});

// ==================== DELETE COMPUTER ====================

const deleteConfirmPopup = document.getElementById("popup-delete-confirm");
const deleteNoBtn = document.getElementById("popup-delete-no");
const deleteYesBtn = document.getElementById("popup-delete-yes");
const deleteButtons = document.querySelectorAll(".room-detail-delete-computer");
let deleteUrl = "";

deleteButtons.forEach(function (btn) {
  btn.addEventListener("click", function (event) {
    event.preventDefault();
    deleteUrl = this.href;
    if (deleteConfirmPopup) {
      deleteConfirmPopup.classList.add("show");
    }
  });
});

deleteNoBtn.addEventListener("click", function () {
  deleteConfirmPopup.classList.remove("show");
  deleteUrl = "";
});

deleteYesBtn.addEventListener("click", function () {
  if (deleteUrl) {
    window.location.href = deleteUrl;
  }
});

// ==================== SUCCESS POPUP ====================

const successInfo = document.getElementById("room-page");
const popupSuccess = document.getElementById("popup-success");
const popupSuccessMessage = document.getElementById("popup-success-message");
const popupSuccessClose = document.getElementById("popup-success-close");

if (successInfo && popupSuccess) {
  const successMessage = successInfo.dataset.success;

  if (successMessage && successMessage.trim() !== "") {
    if (popupSuccessMessage) {
      popupSuccessMessage.textContent = successMessage;
    }

    popupSuccess.classList.add("show");
  }
}

if (popupSuccessClose && popupSuccess) {
  popupSuccessClose.addEventListener("click", function () {
    popupSuccess.classList.remove("show");
  });
}
