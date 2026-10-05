const uploadInput = document.querySelector("[data-document-upload-input]");
const uploadStatus = document.querySelector("[data-document-upload-status]");
const uploadTriggers = document.querySelectorAll("[data-document-upload-trigger]");

if (uploadInput && uploadStatus) {
  const maxUploadSize = 10 * 1024 * 1024;
  const supportedExtensions = new Set(["pdf", "png", "jpg", "jpeg"]);
  const translate = (key, values) => window.LifeGraphI18n?.t(key, values) || key;
  let uploading = false;
  let lastStatus = ["dashboard.uploadIdle", {}];

  const setStatus = (key, values = {}, state = "") => {
    lastStatus = [key, values];
    uploadStatus.textContent = translate(key, values);
    uploadStatus.dataset.state = state;
  };

  uploadTriggers.forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (!uploading) uploadInput.click();
    });
  });

  uploadInput.addEventListener("change", async () => {
    const file = uploadInput.files?.[0];
    if (!file) return;

    const filename = file.name;
    const extension = filename.split(".").pop()?.toLowerCase();
    if (!extension || !supportedExtensions.has(extension)) {
      setStatus("dashboard.uploadFailure", {
        filename,
        message: translate("dashboard.uploadInvalidType"),
      }, "error");
      uploadInput.value = "";
      return;
    }
    if (file.size > maxUploadSize) {
      setStatus("dashboard.uploadFailure", {
        filename,
        message: translate("dashboard.uploadTooLarge"),
      }, "error");
      uploadInput.value = "";
      return;
    }

    uploading = true;
    setStatus("dashboard.uploading", { filename });
    const formData = new FormData();
    formData.append("document", file);

    try {
      const response = await fetch("/api/documents/upload", {
        method: "POST",
        body: formData,
      });
      let payload = {};
      if (response.headers.get("content-type")?.includes("application/json")) {
        payload = await response.json();
      }
      if (!response.ok) throw new Error(payload.error || translate("dashboard.uploadNetworkError"));
      setStatus("dashboard.uploadSuccess", { filename }, "success");
    } catch (error) {
      setStatus("dashboard.uploadFailure", {
        filename,
        message: error instanceof Error ? error.message : translate("dashboard.uploadNetworkError"),
      }, "error");
    } finally {
      uploading = false;
      uploadInput.value = "";
    }
  });

  window.addEventListener("lifegraph:languagechange", () => {
    uploadStatus.textContent = translate(lastStatus[0], lastStatus[1]);
  });
}
