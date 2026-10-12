const addProgramBtn = document.getElementById("program-add-act");
const programFormBox = document.getElementById("program-add-container");
const programForm = document.getElementById("program-form");

const cancelProgramBtn = document.getElementById("cancel-add-program-btn");
const addSubmitBtn = document.getElementById("submit-add-program-btn");
const editSubmitBtn = document.getElementById("submit-edit-program-btn");

const nameProgram = programForm.querySelector('[name="program_name"]');
const versionProgram = programForm.querySelector('[name="program_version"]');
const publisherProgram = programForm.querySelector(
  '[name="program_publisher"]',
);
const imgProgram = programForm.querySelector('[name="program_img"]');

const popupConfirm = document.getElementById("popup-confirm");
const cancelNoBtn = document.getElementById("popup-cancel-no");
const cancelYesBtn = document.getElementById("popup-cancel-yes");

const popupError = document.getElementById("popup-error");
const popupErrorClose = document.getElementById("popup-error-close");
const popupErrorMessage = document.getElementById("popup-error-message");

let isEditing = false;

// show form program
addProgramBtn.addEventListener("click", () => {
  programFormBox.classList.add("show");
});

// add program
programForm.addEventListener("submit", function (e) {
  if (
    nameProgram.value.trim() === "" ||
    versionProgram.value.trim() === "" ||
    publisherProgram.value.trim() === ""
  ) {
    e.preventDefault();
    popupError.classList.add("show");
  }
});

cancelProgramBtn.addEventListener("click", function () {
  if (isEditing) {
    popupConfirm.classList.add("show");
  } else {
    programFormBox.classList.remove("show");
    programForm.reset();
  }
});

popupErrorClose.addEventListener("click", function () {
  popupError.classList.remove("show");
});

//Edit
document.querySelectorAll(".edit-detail-act").forEach(function (button) {
  button.addEventListener("click", function () {
    isEditing = true;

    const id = button.dataset.id;

    nameProgram.value = button.dataset.name;
    versionProgram.value = button.dataset.version;
    publisherProgram.value = button.dataset.publisher;
    imgProgram.value = button.dataset.img;

    programForm.action = `/admin/program/${id}/edit`;

    addSubmitBtn.style.display = "none";
    editSubmitBtn.style.display = "inline-flex";

    programFormBox.classList.add("show");
    nameProgram.focus();
  });
});

cancelNoBtn.addEventListener("click", function () {
  popupConfirm.classList.remove("show");
  programTable.classList.remove("hidden");
});

// cancel confrim: cancel
cancelYesBtn.addEventListener("click", function () {
  popupConfirm.classList.remove("show");
  programFormBox.classList.remove("show");

  programForm.reset();
  programForm.action = "/admin/program";

  isEditing = false;

  addSubmitBtn.style.display = "inline-flex";
  editSubmitBtn.style.display = "none";
});

// Popup thành công
const programPage = document.getElementById("program-page");
const popupSuccess = document.getElementById("popup-success");
const popupSuccessClose = document.getElementById("popup-success-close");

if (programPage && popupSuccess && popupSuccessClose) {
  if (programPage.dataset.success) {
    popupSuccess.classList.add("show");
  }

  popupSuccessClose.addEventListener("click", function () {
    popupSuccess.classList.remove("show");
  });
}

// popup delete
const deleteProgramPopup = document.getElementById("popup-delete-program");
const deleteProgramName = document.getElementById("delete-program-name");
const deleteProgramConfigs = document.getElementById("delete-program-configs");
const deleteProgramEmpty = document.getElementById("delete-program-empty");
const deleteProgramForm = document.getElementById("delete-program-form");
const deleteProgramCancel = document.getElementById("delete-program-cancel");

document.querySelectorAll(".delete-detail-act").forEach(function (button) {
  button.addEventListener("click", async function () {
    const id = button.dataset.id;
    const name = button.dataset.name;

    deleteProgramName.textContent = name;
    // lam rỗng bảng rồi mới thêm vào
    deleteProgramConfigs.replaceChildren();
    deleteProgramEmpty.style.display = "none";
    deleteProgramPopup.classList.add("show");
    deleteProgramForm.action = `/admin/program/${id}/delete`;

    try {
      const response = await fetch(`/admin/program/${id}/compatibility`);

      if (!response.ok) {
        throw new Error("Không thể tải danh sách cấu hình.");
      }

      const configs = await response.json();

      if (configs.length === 0) {
        deleteProgramEmpty.style.display = "block";
        return;
      }

      configs.forEach(function (config, index) {
        const row = document.createElement("tr");

        [
          index + 1,
          `CH${config.MaCauHinh}`,
          config.CPU ?? "",
          config.RAM ?? "",
          config.OCung ?? "",
          config.CardManHinh ?? "",
        ].forEach(function (value) {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.appendChild(cell); //đưa dữ liệu vào hàng
        });

        deleteProgramConfigs.appendChild(row); // đưa hàng vô bảng
      });
    } catch (error) {
      console.error(error);
      deleteProgramConfigs.replaceChildren();

      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 6;
      cell.textContent = "Không tải được danh sách cấu hình. Vui lòng thử lại.";
      row.appendChild(cell);
      deleteProgramConfigs.appendChild(row);
    }
  });
});

deleteProgramCancel.addEventListener("click", function () {
  deleteProgramPopup.classList.remove("show");
  popupSuccess.classList.add("show");
});
