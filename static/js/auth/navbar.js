const headerUser = document.getElementById("headerUser");
const navbarContainer = document.getElementById("navbarContainer");
const navbarArrow = document.querySelector(".navbar-arrow i");

headerUser.addEventListener("click", function (event) {
  event.stopPropagation();
  navbarContainer.classList.toggle("show");

  if (navbarContainer.classList.contains("show")) {
    navbarArrow.classList.remove("fa-chevron-down");
    navbarArrow.classList.add("fa-chevron-up");
  } else {
    navbarArrow.classList.remove("fa-chevron-up");
    navbarArrow.classList.add("fa-chevron-down");
  }
});
