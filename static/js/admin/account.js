const addBtn = document.getElementById("account-add-act");
const formPopup = document.getElementById("account-add-container");
const accountForm = document.getElementById("account-add-form");
const popupTitle = document.getElementById("account-popup-title");

const cancelBtn = document.getElementById("cancel-add-account-btn");
const submitBtn = document.getElementById("submit-add-account-btn");
const closeDetailBtn = document.getElementById("close-see-detail-account-btn");
const toggleStatusBtn = document.getElementById("toggle-account-status-btn");

const successAccountPopup = document.getElementById("popup-success-account");
const successAccountMessage = document.getElementById(
  "popup-success-account-message",
);
const sendMailBtn = document.getElementById("popup-success-account-send");
const closeSuccessAccountBtn = document.getElementById(
  "popup-success-account-close",
);

const successPopup = document.getElementById("popup-success");
const successMessage = document.getElementById("popup-success-message");
const closeSuccessBtn = document.getElementById("popup-success-close");

const errorPopup = document.getElementById("popup-error");
const errorMessage = document.getElementById("popup-error-message");
const closeErrorBtn = document.getElementById("popup-error-close");
const pageData = document.getElementById("account-page");

const deleteBtns = document.querySelectorAll(".delete-detail-act");
const deletePopup = document.getElementById("popup-delete-account");
const deleteForm = document.getElementById("delete-account-form");
const deleteCancelBtn = document.getElementById("delete-account-cancel");

let pendingAccountId = successAccountPopup?.dataset.accountId || null;
let currentDetailAccountId = null;
let currentAccountStatus = null;

// ======ADD ACCOUNT=====
addBtn?.addEventListener("click", () => {
  accountForm.reset();
  currentDetailAccountId = null;
  currentAccountStatus = null;

  accountForm.action = "/admin/account";
  popupTitle.textContent = "Cấp tài khoản";
  submitBtn.textContent = "Cấp tài khoản";

  accountForm.querySelectorAll("input, select, textarea").forEach((field) => {
    field.disabled = false;
    field.readOnly = false;
  });

  submitBtn.hidden = false;
  cancelBtn.hidden = false;
  closeDetailBtn.hidden = true;
  toggleStatusBtn.hidden = true;

  formPopup.hidden = false;
  formPopup.classList.add("show");
});
cancelBtn?.addEventListener("click", () => {
  formPopup.classList.remove("show");
  window.location.reload();
});

accountForm.addEventListener("submit", function (event) {
  const accountEmail = accountForm.querySelector('[name="account_email"]');
  const accountName = accountForm.querySelector('[name="account_name"]');
  const accountBirth = accountForm.querySelector('[name="account_birth"]');
  const accountGender = accountForm.querySelector('[name="account_gender"]');
  const accountTel = accountForm.querySelector('[name="account_tel"]');
  const accountRole = accountForm.querySelector('[name="account_role"]');

  if (
    !accountEmail.value.trim() ||
    !accountName.value.trim() ||
    !accountBirth.value ||
    !accountGender.value ||
    !accountTel.value.trim() ||
    !accountRole.value
  ) {
    event.preventDefault();
    errorMessage.textContent = "Vui lòng điền đầy đủ thông tin.";
    errorPopup.classList.add("show");
    return;
  }

  if (
    !["0", "1"].includes(accountGender.value) ||
    !["0", "1"].includes(accountRole.value)
  ) {
    event.preventDefault();
    errorMessage.textContent = "Giới tính hoặc vai trò không hợp lệ.";
    errorPopup.classList.add("show");
  }
});
// ======= SEE DETAIL ======
document.querySelectorAll(".see-detail-act").forEach((button) => {
  button.addEventListener("click", async () => {
    const id = button.dataset.id;
    if (!id) {
      errorMessage.textContent = "Không tìm thấy mã tài khoản.";
      errorPopup.classList.add("show");
      return;
    }

    try {
      const response = await fetch(`/admin/account/${id}/detail`);
      const data = await response.json();

      if (!response.ok || data.error) {
        errorMessage.textContent =
          typeof data.error === "string"
            ? data.error
            : "Không lấy được thông tin tài khoản.";
        errorPopup.classList.add("show");
        return;
      }

      accountForm.reset();
      currentDetailAccountId = data.id;
      currentAccountStatus = Number(data.status);

      popupTitle.textContent = "Chi tiết tài khoản";

      document.getElementById("account_email").value = data.email ?? "";
      document.getElementById("account_name").value = data.name ?? "";
      document.getElementById("account_birth").value = data.birth ?? "";
      document.getElementById("account_tel").value = data.tel ?? "";

      accountForm
        .querySelectorAll('input[name="account_gender"]')
        .forEach((radio) => {
          radio.checked = String(data.gender) === radio.value;
        });

      accountForm
        .querySelectorAll('input[name="account_role"]')
        .forEach((radio) => {
          radio.checked = String(data.role) === radio.value;
        });

      accountForm
        .querySelectorAll("input, select, textarea")
        .forEach((field) => {
          field.disabled = true;
          field.readOnly = true;
        });

      submitBtn.hidden = true;
      cancelBtn.hidden = true;
      closeDetailBtn.hidden = false;
      toggleStatusBtn.hidden = false;
      formPopup.hidden = false;

      toggleStatusBtn.textContent =
        currentAccountStatus === 1 ? "Khóa tài khoản" : "Mở khóa tài khoản";

      formPopup.classList.add("show");
    } catch (error) {
      errorMessage.textContent = "Lỗi kết nối khi lấy chi tiết tài khoản.";
      errorPopup.classList.add("show");
    }
  });
});
closeDetailBtn?.addEventListener("click", () => {
  formPopup.classList.remove("show");
});

// =============LOCK - UNLOCK ========================
toggleStatusBtn?.addEventListener("click", async () => {
  if (!currentDetailAccountId || currentAccountStatus === null) {
    errorMessage.textContent = "Không xác định được tài khoản.";
    errorPopup.classList.add("show");
    return;
  }

  const body = new URLSearchParams();
  body.set("status", String(currentAccountStatus === 1 ? 0 : 1));

  toggleStatusBtn.disabled = true;

  try {
    const response = await fetch(
      `/admin/account/${currentDetailAccountId}/status`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        },
        body: body.toString(),
      },
    );

    if (!response.ok) {
      errorMessage.textContent = "Không cập nhật được trạng thái tài khoản.";
      errorPopup.classList.add("show");
      return;
    }

    window.location.reload();
  } catch (error) {
    errorMessage.textContent = "Lỗi kết nối khi cập nhật trạng thái.";
    errorPopup.classList.add("show");
  } finally {
    toggleStatusBtn.disabled = false;
  }
});

// =============GUI MAIL ====================
sendMailBtn?.addEventListener("click", async () => {
  if (!pendingAccountId) {
    successMessage.textContent = "Không tìm thấy tài khoản cần gửi email.";
    return;
  }

  sendMailBtn.disabled = true;
  sendMailBtn.textContent = "Đang gửi...";

  try {
    const response = await fetch(
      `/admin/account/send-email/${pendingAccountId}`,
      {
        method: "POST",
        headers: { Accept: "application/json" },
      },
    );

    const result = await response.json();
    successMessage.textContent =
      result.message || "Không nhận được phản hồi từ máy chủ.";

    if (response.ok && result.success) {
      sendMailBtn.hidden = true;
    }
  } catch (error) {
    successMessage.textContent = "Lỗi kết nối. Vui lòng thử lại.";
  } finally {
    sendMailBtn.disabled = false;

    if (!sendMailBtn.hidden) {
      sendMailBtn.textContent = "Gửi mail";
    }
  }
});

closeSuccessBtn?.addEventListener("click", () => {
  successPopup.classList.remove("show");
});
closeSuccessAccountBtn?.addEventListener("click", () => {
  successAccountPopup.classList.remove("show");
});
closeErrorBtn?.addEventListener("click", () => {
  errorPopup.classList.remove("show");
});

// ======POPUP ======
if (pageData?.dataset.success) {
  successMessage.textContent = pageData.dataset.success;
  successPopup.classList.add("show");
} else {
  successPopup.classList.remove("show");
}
if (pendingAccountId && pageData?.dataset.accountCreated === "true") {
  successAccountPopup.classList.add("show");
} else {
  successAccountPopup.classList.remove("show");
}
if (pageData?.dataset.error) {
  errorMessage.textContent = pageData.dataset.error;
  errorPopup.classList.add("show");
}

// ====== DELETE ACCOUNT ======

deleteBtns.forEach((button) => {
  button.addEventListener("click", async () => {
    const accountId = button.dataset.id;

    try {
      const response = await fetch(`/admin/account/${accountId}/detail`);
      const data = await response.json();

      if (!response.ok || data.error) {
        errorMessage.textContent = "Không lấy được thông tin tài khoản.";
        errorPopup.classList.add("show");
        return;
      }

      deleteForm.action = `/admin/account/${data.role}/${accountId}/delete`;
      deletePopup.classList.add("show");
    } catch (error) {
      errorMessage.textContent = "Lỗi khi lấy thông tin tài khoản.";
      errorPopup.classList.add("show");
    }
  });
});
deleteCancelBtn.addEventListener("click", () => {
  deletePopup.classList.remove("show");
});
