const headerUser = document.getElementById("headerUser");
const navbarContainer = document.getElementById("navbarContainer");

headerUser.addEventListener("click", function (event) {
  event.stopPropagation();
  navbarContainer.classList.toggle("show");
});

document.addEventListener("click", function () {
  navbarContainer.classList.remove("show");
});
