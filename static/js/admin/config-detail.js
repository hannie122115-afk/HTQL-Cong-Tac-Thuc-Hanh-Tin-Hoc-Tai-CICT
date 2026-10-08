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

// SUCCESS POPUP

const configDetailPage = document.getElementById("config-page");
const successDetail = configDetailPage.dataset.success;
const popupDetailSuccess = document.getElementById("popup-success");
const popupDetailSuccessClose = document.getElementById("popup-success-close");

if (successDetail) {
  popupDetailSuccess.classList.add("show");
}

popupDetailSuccessClose.addEventListener("click", function () {
  popupDetailSuccess.classList.remove("show");
});
