(() => {
  function initRoomPage() {
    const page = document.getElementById("room-page");
    if (page?.dataset.roomEventsBound === "true") return;
    if (page) page.dataset.roomEventsBound = "true";

    const errorPopup = document.getElementById("popup-error");
    const errorMessage = document.getElementById("popup-error-message");
    function showError(message) {
      if (errorPopup && errorMessage) {
        errorMessage.textContent = message;
        errorPopup.hidden = false;
        errorPopup.classList.add("show");
      } else {
        window.alert(message);
      }
    }
    document.getElementById("popup-error-close")?.addEventListener("click", () => {
      errorPopup?.classList.remove("show");
    });

    // Gắn luồng Xóa trước, độc lập với form Thêm phòng.
    const deletePopup = document.getElementById("popup-delete-room");
    const deleteForm = document.getElementById("delete-room-form");
    const deleteConfirm = document.getElementById("delete-room-confirm");
    const deleteName = document.getElementById("delete-room-name");

    // Delegation nhận cả click lên biểu tượng bên trong nút và các dòng được vẽ lại.
    document.addEventListener("click", (event) => {
      const button = event.target.closest?.(".room-table button.delete-detail-act");
      if (!button) return;
      event.preventDefault();
      const id = button.dataset.id;
      if (!id || !/^\d+$/.test(id)) {
        showError("Không xác định được mã phòng!");
        return;
      }
      if (!deletePopup || !deleteForm || !deleteConfirm) {
        showError("Không tải được hộp xác nhận xóa phòng. Vui lòng tải lại trang.");
        return;
      }
      deleteForm.action = `/admin/room/${id}/delete`;
      if (deleteName) deleteName.textContent = button.dataset.roomName || id;
      deleteConfirm.disabled = false;
      deleteConfirm.textContent = "Xác nhận xóa";
      deletePopup.hidden = false;
      deletePopup.setAttribute("aria-hidden", "false");
      deletePopup.classList.add("show");
    });

    document.getElementById("delete-room-cancel")?.addEventListener("click", () => {
      deletePopup?.classList.remove("show");
      deletePopup?.setAttribute("aria-hidden", "true");
    });
    deleteForm?.addEventListener("submit", (event) => {
      if (!deleteForm.getAttribute("action")) {
        event.preventDefault();
        showError("Vui lòng chọn phòng cần xóa.");
        return;
      }
      if (deleteConfirm) {
        deleteConfirm.disabled = true;
        deleteConfirm.textContent = "Đang xóa…";
      }
    });

    const addPopup = document.getElementById("room-add-container");
    const addForm = document.getElementById("room-add-form");
    document.getElementById("room-add-act")?.addEventListener("click", () => {
      addPopup?.classList.add("show");
    });
    document.getElementById("cancel-add-config-btn")?.addEventListener("click", () => {
      addPopup?.classList.remove("show");
    });
    addForm?.addEventListener("submit", (event) => {
      const name = addForm.querySelector('[name="room_name"]');
      const config = addForm.querySelector('[name="config_id"]');
      const staff = addForm.querySelector('[name="staff_id"]');
      const machines = addForm.querySelector('[name="machine_count"]');
      let message = "";
      let inputError = null;
      if (!name?.value.trim() || !config?.value || !staff?.value) {
        message = "Vui lòng nhập đầy đủ thông tin!";
        inputError = name;
      } else if (!machines?.value.trim() || !Number.isInteger(Number(machines.value)) ||
                 Number(machines.value) < 1 || Number(machines.value) > 60) {
        message = "Số lượng máy tính phải từ 1 đến 60!";
        inputError = machines;
      }
      if (message) {
        event.preventDefault();
        showError(message);
        inputError?.focus();
      }
    });

    if (page?.dataset.error) showError(page.dataset.error);
    if (page?.dataset.success) {
      document.getElementById("popup-success")?.classList.add("show");
      setTimeout(() => window.location.reload(), 300);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRoomPage, { once: true });
  } else {
    initRoomPage();
  }
})();
