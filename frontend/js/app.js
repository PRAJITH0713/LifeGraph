const currentPath = window.location.pathname;
const currentPage = currentPath === "/" ? "/" : currentPath;

for (const link of document.querySelectorAll(".site-nav a")) {
  if (link.getAttribute("href") === currentPage) {
    link.setAttribute("aria-current", "page");
  }
}

const apiStatus = document.querySelector("[data-api-status]");
if (apiStatus) {
  fetch("/api/health")
    .then((response) => {
      if (!response.ok) throw new Error("API unavailable");
      return response.json();
    })
    .then(() => {
      apiStatus.textContent = "API online";
      apiStatus.dataset.state = "online";
    })
    .catch(() => {
      apiStatus.textContent = "API offline";
      apiStatus.dataset.state = "offline";
    });
}

for (const logo of document.querySelectorAll("[data-brand-logo]")) {
  const hideMissingLogo = () => logo.remove();
  if (logo.complete && logo.naturalWidth === 0) {
    hideMissingLogo();
  } else {
    logo.addEventListener("error", hideMissingLogo, { once: true });
  }
}
