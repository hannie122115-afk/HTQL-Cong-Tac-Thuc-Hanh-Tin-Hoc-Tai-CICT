const addRoom = document.getElementById("room-add-act");
const addRoomFormBox = document.getElementById("room-add-container");
const addRoomForm = document.getElementById("room-add-form");
const cancelRoomBtn = document.getElementById("cancel-add-config-btn");

addRoom.addEventListener("click", function (e) {
  e.stopPropagation();
  addRoomFormBox.classList.add("show");
});
cancelRoomBtn.addEventListener("click", function () {
  addRoomFormBox.classList.remove("show");
});

// add room
const roomName = document.querySelector('input[name="room_name"]');
const configId = document.querySelector('select[name="config_id"]');
const staffId = document.querySelector('select[name="staff_id"]');
const machineCount = document.querySelector('input[name="machine_count"]');

const popupError = document.getElementById("popup-error");
const popupErrorMessage = document.getElementById("popup-error-message");
const popupErrorClose = document.getElementById("popup-error-close");

addRoomForm.addEventListener("submit", function (e) {
  let message = "";
  let inputError = null;

  if (
    roomName.value.trim() === "" ||
    configId.value === "" ||
    staffId.value === ""
  ) {
    message = "Vui lòng nhập đầy đủ thông tin!";
    inputError = roomName;
  } else if (
    machineCount.value.trim() === "" ||
    !Number.isInteger(Number(machineCount.value)) ||
    Number(machineCount.value) < 1 ||
    Number(machineCount.value) > 60
  ) {
    message = "Số lượng máy tính phải từ 1 đến 60!";
    inputError = machineCount;
  }

  if (message !== "") {
    e.preventDefault();

    popupErrorMessage.textContent = message;
    popupError.classList.add("show");

    if (inputError) {
      inputError.focus();
    }
  }
});
popupErrorClose.addEventListener("click", function () {
  popupError.classList.remove("show");
});

// success popup
const popupSuccess = document.getElementById("popup-success");
const popupSuccessClose = document.getElementById("popup-success-close");
const roomPage = document.getElementById("config-page");
const success = roomPage.dataset.success;

if (success && success.trim() !== "") {
  popupSuccess.classList.add("show");
}
popupSuccessClose.addEventListener("click", function () {
  popupSuccess.classList.remove("show");
});

// popup confirm delete
const deleteRoomPopup = document.getElementById("popup-delete-room");
const deleteRoomForm = document.getElementById("delete-room-form");
const deleteRoomCancel = document.getElementById("delete-room-cancel");

document.querySelectorAll(".delete-detail-act").forEach(function (button) {
  button.addEventListener("click", function () {
    const id = button.dataset.id;

    if (!id) {
      popupErrorMessage.textContent = "Không xác định được mã phòng!";
      popupError.classList.add("show");
      return;
    }

    deleteRoomForm.action = `/admin/room/${id}/delete`;
    deleteRoomPopup.classList.add("show");
  });
});

deleteRoomCancel.addEventListener("click", function () {
  deleteRoomPopup.classList.remove("show");
});
