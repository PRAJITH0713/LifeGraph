const uploadInput = document.querySelector("[data-document-upload-input]");
const uploadStatus = document.querySelector("[data-document-upload-status]");
const uploadButton = document.querySelector("[data-document-upload-confirm]");
const documentList = document.querySelector("[data-document-list]");
const uploadTriggers = document.querySelectorAll("[data-document-upload-trigger]");

if (uploadInput && uploadStatus && uploadButton) {
  const maxUploadSize = 10 * 1024 * 1024;
  const supportedExtensions = new Set(["pdf", "png", "jpg", "jpeg"]);
  const translate = (key, values) => window.LifeGraphI18n?.t(key, values) || key;
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  let uploading = false;
  let selectedFile = null;
  let selectedFileValid = false;
  let lastStatus = ["dashboard.uploadIdle", {}];

  const setStatus = (key, values = {}, state = "") => {
    lastStatus = [key, values];
    uploadStatus.textContent = translate(key, values);
    uploadStatus.dataset.state = state;
  };

  const formatSize = (size) => {
    if (size < 1024 * 1024) {
      return translate("dashboard.uploadSizeKb", {
        size: Math.max(1, Math.ceil(size / 1024)),
      });
    }
    return translate("dashboard.uploadSizeMb", {
      size: (size / (1024 * 1024)).toFixed(2),
    });
  };

  const setUploadButton = (busy) => {
    uploadButton.disabled = busy || !selectedFileValid;
    uploadButton.setAttribute("aria-busy", String(busy));
    uploadButton.textContent = busy
      ? translate("dashboard.uploadingButton")
      : translate("dashboard.confirmUpload");
  };

  const isSupported = (file) => {
    const extension = file.name.split(".").pop()?.toLowerCase();
    return extension && supportedExtensions.has(extension);
  };

  const appendUploadedDocument = (id, filename, size) => {
    if (!documentList) return;
    if (!documentList.querySelector("[data-document-id]")) {
      documentList.replaceChildren();
    }
    const row = document.createElement("li");
    row.className = "uploaded-document";
    row.dataset.documentId = id;

    const icon = document.createElement("span");
    icon.className = "file-icon file-green";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "✓";

    const name = document.createElement("span");
    name.className = "document-name";
    const title = document.createElement("a");
    title.href = `/api/documents/${encodeURIComponent(id)}`;
    title.textContent = filename;
    const details = document.createElement("small");
    details.textContent = translate("dashboard.uploadedDocumentSize", {
      size: formatSize(size),
    });
    name.append(title, details);

    const state = document.createElement("span");
    state.className = "document-state state-available";
    state.textContent = translate("dashboard.uploaded");
    const remove = document.createElement("button");
    remove.className = "document-delete";
    remove.type = "button";
    remove.textContent = translate("dashboard.deleteDocument");
    remove.addEventListener("click", async () => {
      remove.disabled = true;
      try {
        const response = await fetch(`/api/documents/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: { "X-CSRFToken": csrfToken },
        });
        if (!response.ok) throw new Error(translate("dashboard.deleteFailure"));
        row.remove();
        if (!documentList.querySelector("[data-document-id]")) {
          showEmptyDocumentMessage();
        }
      } catch {
        remove.disabled = false;
        setStatus("dashboard.deleteFailure", {}, "error");
      }
    });
    row.append(icon, name, state, remove);
    documentList.append(row);
  };

  const showEmptyDocumentMessage = () => {
    if (!documentList) return;
    documentList.replaceChildren();
    const empty = document.createElement("li");
    empty.className = "empty-document-state";
    empty.textContent = translate("dashboard.noPrivateDocuments");
    documentList.append(empty);
  };

  const loadDocuments = async () => {
    if (!documentList) return;
    try {
      const response = await fetch("/api/documents");
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || translate("dashboard.uploadNetworkError"));
      documentList.replaceChildren();
      if (!payload.documents.length) {
        showEmptyDocumentMessage();
        return;
      }
      for (const document of payload.documents) {
        appendUploadedDocument(document.id, document.filename, document.size);
      }
    } catch {
      setStatus("dashboard.uploadFailure", {
        filename: "",
        message: translate("dashboard.uploadNetworkError"),
      }, "error");
    }
  };

  uploadTriggers.forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (!uploading) uploadInput.click();
    });
  });

  uploadInput.addEventListener("change", () => {
    const file = uploadInput.files?.[0];
    if (!file) return;

    selectedFile = file;
    selectedFileValid = false;
    if (!isSupported(file)) {
      setStatus("dashboard.uploadFailure", {
        filename: file.name,
        message: translate("dashboard.uploadInvalidType"),
      }, "error");
      setUploadButton(false);
      return;
    }
    if (file.size > maxUploadSize) {
      setStatus("dashboard.uploadFailure", {
        filename: file.name,
        message: translate("dashboard.uploadTooLarge"),
      }, "error");
      setUploadButton(false);
      return;
    }

    setStatus("dashboard.uploadReady", {
      filename: file.name,
      size: formatSize(file.size),
    }, "ready");
    selectedFileValid = true;
    setUploadButton(false);
  });

  uploadButton.addEventListener("click", async () => {
    if (!selectedFile || !selectedFileValid || uploading || !isSupported(selectedFile)) return;
    if (selectedFile.size > maxUploadSize) {
      setStatus("dashboard.uploadFailure", {
        filename: selectedFile.name,
        message: translate("dashboard.uploadTooLarge"),
      }, "error");
      return;
    }

    uploading = true;
    setStatus("dashboard.uploading", { filename: selectedFile.name }, "loading");
    setUploadButton(true);

    const formData = new FormData();
    formData.append("document", selectedFile);
    try {
      const response = await fetch("/api/documents/upload", {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: formData,
      });
      let payload = {};
      if (response.headers.get("content-type")?.includes("application/json")) {
        payload = await response.json();
      }
      if (
        response.status !== 201
        || typeof payload.id !== "string"
        || typeof payload.filename !== "string"
        || !Number.isFinite(payload.size)
      ) {
        throw new Error(payload.error || translate("dashboard.uploadNetworkError"));
      }

      appendUploadedDocument(payload.id, payload.filename, payload.size);
      setStatus("dashboard.uploadSuccess", {
        filename: payload.filename,
        size: formatSize(payload.size),
      }, "success");
      selectedFile = null;
      selectedFileValid = false;
      uploadInput.value = "";
    } catch (error) {
      setStatus("dashboard.uploadFailure", {
        filename: selectedFile.name,
        message: error instanceof Error
          ? error.message
          : translate("dashboard.uploadNetworkError"),
      }, "error");
    } finally {
      uploading = false;
      setUploadButton(false);
      loadDocuments();
    }
  });

  window.addEventListener("lifegraph:languagechange", () => {
    uploadStatus.textContent = translate(lastStatus[0], lastStatus[1]);
    uploadButton.textContent = uploading
      ? translate("dashboard.uploadingButton")
      : translate("dashboard.confirmUpload");
  });

  setUploadButton(false);
}
