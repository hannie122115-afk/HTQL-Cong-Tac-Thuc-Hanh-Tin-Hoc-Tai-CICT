// EDIT / CANCEL / SAVE
const editBtn = document.getElementById("config-edit-btn");
const cancelBtn = document.getElementById("config-cancel-btn");
const saveBtn = document.getElementById("config-save-btn");

const configValues = document.querySelectorAll(
  ".config-detail-item-info > .config-value:not(.room-value)",
);

const configInputs = document.querySelectorAll(".config-input");

const roomValue = document.querySelector(".room-value");
const roomBox = document.getElementById("config-room-box");

// EDIT
editBtn.addEventListener("click", function () {
  editBtn.style.display = "none";
  cancelBtn.style.display = "inline-flex";
  saveBtn.style.display = "inline-flex";

  configValues.forEach(function (element) {
    element.style.display = "none";
  });

  configInputs.forEach(function (input) {
    input.style.display = "block";
  });

  roomValue.style.display = "none";
  roomBox.style.display = "flex";
});

// ROOM DROPDOWN
const roomConfigTitle = document.getElementById("config-room-title");

if (roomConfigTitle) {
  roomConfigTitle.addEventListener("click", function (e) {
    e.stopPropagation();

    roomBox.classList.toggle("show");
  });
}

// CANCEL EDIT
const popupConfirm = document.getElementById("popup-confirm");
const popupCancelNo = document.getElementById("popup-cancel-no");
const popupCancelYes = document.getElementById("popup-cancel-yes");

cancelBtn.addEventListener("click", function () {
  popupConfirm.classList.add("show");
});

popupCancelNo.addEventListener("click", function () {
  popupConfirm.classList.remove("show");
});

popupCancelYes.addEventListener("click", function () {
  popupConfirm.classList.remove("show");

  window.location.reload();
});

// SUCCESS EDIT CONFIG POPUP

const popupSuccess = document.getElementById("popup-success");
const popupSuccessMessage = document.getElementById("popup-success-message");
const popupSuccessClose = document.getElementById("popup-success-close");

const configPage = document.getElementById("config-page");

const successMessage = configPage.dataset.success;

if (successMessage) {
  popupSuccessMessage.textContent = successMessage;
  popupSuccess.classList.add("show");
}

popupSuccessClose.addEventListener("click", function () {
  popupSuccess.classList.remove("show");
});

// ADD PROGRAM DETAIL
const addProgramBtn = document.getElementById("config-detail-add-act");
const saveProgramBtn = document.getElementById("config-detail-save-act");
const programFormContainer = document.getElementById(
  "program-form-container",
);

addProgramBtn.addEventListener("click", function () {
  programFormContainer.classList.add("show");

  addProgramBtn.style.display = "none";

  saveProgramBtn.style.display = "inline-flex";
});

// CONFIRM DELETE PROGRAM POPUP
const deleteConfirmPopup = document.getElementById("popup-delete-confirm");
const deleteNoBtn = document.getElementById("popup-delete-no");
const deleteYesBtn = document.getElementById("popup-delete-yes");

let deleteUrl = "";

const deleteButtons = document.querySelectorAll(
  ".config-detail-delete-program",
);
deleteButtons.forEach(function (btn) {
  btn.addEventListener("click", function (e) {
    e.preventDefault();
    deleteUrl = this.href;
    deleteConfirmPopup.classList.add("show");
  });
});

deleteNoBtn.addEventListener("click", function () {
  deleteConfirmPopup.classList.remove("show");
});

deleteYesBtn.addEventListener("click", function () {
  window.location.href = deleteUrl;
});
