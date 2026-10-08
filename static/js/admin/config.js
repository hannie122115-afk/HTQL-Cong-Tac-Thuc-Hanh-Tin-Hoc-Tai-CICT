const addConfig = document.getElementById("config-add-act");
const addConfigForm = document.getElementById("config-add-container");
const cancelConfigBtn = document.getElementById("cancel-add-config-btn");

addConfig.addEventListener("click", function (e) {
  e.stopPropagation();
  addConfigForm.classList.toggle("show");
});

cancelConfigBtn.addEventListener("click", function () {
  addConfigForm.classList.remove("show");
});

// room

const roomConfigTitle = document.getElementById("config-room-title");
const configRoomBox = document.getElementById("config-room-box");

roomConfigTitle.addEventListener("click", function (e) {
  e.stopPropagation();
  configRoomBox.classList.toggle("show");
});

// add config
const cpu = document.querySelector('input[name="cpu"]');
const ram = document.querySelector('input[name="ram"]');
const hardDrive = document.querySelector('input[name="hard_drive"]');
const screenCard = document.querySelector('input[name="screen_card"]');

const popupError = document.getElementById("popup-error");
const popupErrorClose = document.getElementById("popup-error-close");

addConfigForm.addEventListener("submit", function (e) {
  if (
    cpu.value.trim() === "" ||
    ram.value.trim() === "" ||
    hardDrive.value.trim() === "" ||
    screenCard.value.trim() === ""
  ) {
    e.preventDefault();
    popupError.classList.add("show");
  }
});

popupErrorClose.addEventListener("click", function () {
  popupError.classList.remove("show");
});

// pop up success
const popupSuccess = document.getElementById("popup-success");
const popupSuccessClose = document.getElementById("popup-success-close");
const configPage = document.getElementById("config-page");
const success = configPage.dataset.success;

if (success) {
  popupSuccess.classList.add("show");
}

popupSuccessClose.addEventListener("click", function () {
  popupSuccess.classList.remove("show");
});
