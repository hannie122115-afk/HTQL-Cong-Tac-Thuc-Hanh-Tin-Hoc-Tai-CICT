const informationForm = document.getElementById("information-form");
const passwordForm = document.getElementById("password-form");
const profilePage = document.getElementById("staff-user-page");
const popupError = document.getElementById("popup-error");
const popupErrorMessage = document.getElementById("popup-error-message");
const popupErrorClose = document.getElementById("popup-error-close");
const popupSuccess = document.getElementById("popup-success");
let inputToFocus = null;
const newPassword = document.getElementById("new-password");
const confirmPassword = document.getElementById("confirm-password");

function showProfileError(message, input = null) {
  popupErrorMessage.textContent = message;
  inputToFocus = input;
  popupError.classList.add("show");
  popupError.setAttribute("aria-hidden", "false");
  popupErrorClose.focus();
}

function closeProfileError() {
  popupError.classList.remove("show");
  popupError.setAttribute("aria-hidden", "true");
  inputToFocus?.focus();
  inputToFocus = null;
}

popupErrorClose.addEventListener("click", closeProfileError);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && popupError.classList.contains("show"))
    closeProfileError();
});

[informationForm, passwordForm].forEach((form) => {
  form.addEventListener(
    "invalid",
    (event) => {
      event.preventDefault();
      if (!popupError.classList.contains("show")) {
        const field = event.target;
        const message = field.validity.valueMissing
          ? "Vui lòng điền đầy đủ thông tin, không được bỏ trống."
          : "Thông tin nhập không hợp lệ. Vui lòng kiểm tra lại.";
        field.setAttribute("aria-invalid", "true");
        showProfileError(message, field);
      }
    },
    true,
  );
});

if (profilePage.dataset.error) {
  const form =
    profilePage.dataset.errorScope === "password"
      ? passwordForm
      : informationForm;
  const field = form.elements.namedItem(profilePage.dataset.errorField);
  field?.setAttribute("aria-invalid", "true");
  showProfileError(profilePage.dataset.error, field);
} else if (profilePage.dataset.success) {
  popupSuccess.classList.add("show");
  popupSuccess.setAttribute("aria-hidden", "false");
  window.setTimeout(() => window.location.reload(), 300);
}

document.querySelectorAll(".toggle-password").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.target);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.setAttribute("aria-pressed", String(show));
    button.setAttribute("aria-label", `${show ? "Ẩn" : "Hiện"} mật khẩu`);
    input.focus();
  });
});

passwordForm.addEventListener("submit", (event) => {
  confirmPassword.removeAttribute("aria-invalid");
  let message = "";
  if (
    !/^(?=.{8,128}$)(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).*$/.test(
      newPassword.value,
    )
  ) {
    message =
      "Mật khẩu mới cần 8–128 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt.";
  } else if (newPassword.value !== confirmPassword.value) {
    message = "Mật khẩu xác nhận không khớp.";
    confirmPassword.setAttribute("aria-invalid", "true");
  }
  if (message) {
    event.preventDefault();
    showProfileError(
      message,
      newPassword.value !== confirmPassword.value
        ? confirmPassword
        : newPassword,
    );
  }
});

passwordForm.addEventListener("input", () => {
  confirmPassword.removeAttribute("aria-invalid");
});
passwordForm.addEventListener("reset", () => {
  passwordForm.querySelectorAll(".password-input input").forEach((input) => {
    input.type = "password";
    input.removeAttribute("aria-invalid");
  });
  passwordForm.querySelectorAll(".toggle-password").forEach((button) => {
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-label", "Hiện mật khẩu");
  });
});

informationForm.addEventListener("submit", (event) => {
  for (const name of ["name", "phone", "birthday", "gender"]) {
    const field = informationForm.elements[name];
    if (!field.value.trim()) {
      event.preventDefault();
      field.setAttribute("aria-invalid", "true");
      showProfileError(
        "Vui lòng điền đầy đủ thông tin, không được bỏ trống.",
        field,
      );
      return;
    }
  }
});

informationForm.addEventListener("input", (event) => {
  event.target.removeAttribute("aria-invalid");
});
