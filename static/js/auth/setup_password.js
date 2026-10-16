const setupPasswordForm = document.getElementById("setup-password-form");
const setupPasswordBtn = document.getElementById("setup-password-btn");
const errorConfirmPopup = document.getElementById("popup-confirm-error");
const errorConfirmMessage = document.getElementById(
  "popup-confirm-error-message",
);
const serverError = document.getElementById("serverError");

setupPasswordForm?.addEventListener("submit", (event) => {
  const token = document.getElementById("token")?.value.trim() || "";
  const password = document.getElementById("password")?.value || "";
  const confirmPassword =
    document.getElementById("confirm_password")?.value || "";

  let message = "";

  if (!token) {
    message = "Liên kết thiết lập mật khẩu không hợp lệ.";
  } else if (!password.trim()) {
    message = "Vui lòng nhập mật khẩu mới.";
  } else if (!confirmPassword.trim()) {
    message = "Vui lòng nhập mật khẩu xác nhận.";
  } else if (password.length < 8) {
    message = "Mật khẩu phải có ít nhất 8 ký tự.";
  } else if (!/[A-Z]/.test(password)) {
    message = "Mật khẩu phải có ít nhất 1 chữ cái viết hoa (A-Z).";
  } else if (!/[a-z]/.test(password)) {
    message = "Mật khẩu phải có ít nhất 1 chữ cái viết thường (a-z).";
  } else if (!/[0-9]/.test(password)) {
    message = "Mật khẩu phải có ít nhất 1 chữ số (0-9).";
  } else if (!/[^A-Za-z0-9]/.test(password)) {
    message = "Mật khẩu phải có ít nhất 1 ký tự đặc biệt (ví dụ: @, #, !).";
  } else if (password !== confirmPassword) {
    message = "Mật khẩu xác nhận không khớp.";
  }

  if (message) {
    event.preventDefault();
    errorConfirmMessage.textContent = message;
    errorConfirmPopup.classList.add("show");
  } else {
    errorConfirmPopup.classList.remove("show");
  }
});

document
  .getElementById("popup-confirm-error-close")
  ?.addEventListener("click", () => {
    errorConfirmPopup?.classList.remove("show");
  });

if (serverError?.textContent.trim()) {
  errorConfirmMessage.textContent = serverError.textContent.trim();
  errorConfirmPopup.classList.add("show");
}
