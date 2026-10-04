const serviceRoot = document.querySelector("[data-service-app]");
const checklistRoot = document.querySelector("[data-checklist-app]");

if (serviceRoot || checklistRoot) {
	const selectedKey = "lifegraph.selectedServiceId";
	const progressKey = "lifegraph.checklistProgress";
	const reminderKeys = [
		"service.reminderConfirm",
		"service.reminderAvailability",
	];
	const t = (key, values) => window.LifeGraphI18n?.t(key, values) || key;
	const detail = document.querySelector("[data-service-detail]");
	const feedback = document.querySelector("[data-catalogue-feedback]");
	const search = document.querySelector("[data-service-search]");
	let services = [];
	let selectedService = null;
	let feedbackKey = "service.feedbackLoading";
	let serviceLoadError = false;

	const showFeedback = (key) => {
		feedbackKey = key;
		if (feedback) feedback.textContent = t(key);
	};

	const renderEmptyChecklist = () => {
		detail?.replaceChildren(make("p", "empty-state", t("checklist.chooseService")));
	};

	const make = (tag, className, text) => {
		const element = document.createElement(tag);
		if (className) element.className = className;
		if (text !== undefined) element.textContent = text;
		return element;
	};

	const readProgress = () => {
		try {
			const stored = JSON.parse(localStorage.getItem(progressKey) || "{}");
			return stored && typeof stored === "object" ? stored : {};
		} catch {
			return {};
		}
	};

	const saveReminderState = (serviceId, index, checked) => {
		try {
			const progress = readProgress();
			const state = Array.isArray(progress[serviceId]) ? progress[serviceId] : [];
			state[index] = checked;
			progress[serviceId] = state;
			localStorage.setItem(progressKey, JSON.stringify(progress));
		} catch {
			showFeedback("service.feedbackStorage");
		}
	};

	const renderChecklist = (service, target) => {
		const requirementsPanel = make("section", "checklist-section");
		requirementsPanel.append(make("h3", "detail-section-title", t("service.requirementsHeading")));
		const statusKey = service.verification_status === "verified"
			? "service.verified"
			: "service.needsVerification";
		requirementsPanel.append(make("span", "verification-badge", t(statusKey)));
		if (service.requirements.length) {
			if (window.LifeGraphI18n?.language === "ta") {
				requirementsPanel.append(make("p", "verification-message", t("service.requirementTranslationNote")));
			}
			const requirementList = make("ul", "requirement-list");
			for (const requirement of service.requirements) {
				requirementList.append(make("li", "", requirement));
			}
			requirementsPanel.append(requirementList);
		} else {
			requirementsPanel.append(make("p", "verification-message", t("service.requirementsUnverified")));
			requirementsPanel.append(make("p", "empty-requirements", t("service.noProofItems")));
		}
		target.append(requirementsPanel);

		const reminderPanel = make("section", "checklist-section reminder-section");
		const heading = make("div", "reminder-heading");
		heading.append(make("h3", "detail-section-title", t("service.remindersHeading")));
		heading.append(make("span", "demo-label", t("service.demoNotRequirements")));
		reminderPanel.append(heading);
		reminderPanel.append(make("p", "reminder-caption", t("service.reminderDescription")));

		const saved = readProgress()[service.id] || [];
		const doneCount = reminderKeys.reduce((count, _, index) => count + (saved[index] ? 1 : 0), 0);
		const progressLabel = make("p", "progress-label", t("service.reminderProgress", { done: doneCount, total: reminderKeys.length }));
		const progress = make("progress", "checklist-progress");
		progress.max = reminderKeys.length;
		progress.value = doneCount;
		progress.setAttribute("aria-label", t("service.progressLabel"));
		reminderPanel.append(progressLabel, progress);

		const list = make("div", "reminder-list");
		reminderKeys.forEach((reminderKey, index) => {
			const label = make("label", "reminder-item");
			const input = document.createElement("input");
			input.type = "checkbox";
			input.setAttribute("aria-label", t(reminderKey));
			input.checked = Boolean(saved[index]);
			input.addEventListener("change", () => {
				saveReminderState(service.id, index, input.checked);
				renderDetails(service, target);
			});
			label.append(input, make("span", "", t(reminderKey)));
			list.append(label);
		});
		reminderPanel.append(list);
		target.append(reminderPanel);
	};

	const renderDetails = (service, target = detail) => {
		if (!target) return;
		target.replaceChildren();
		const header = make("div", "detail-header");
		header.append(make("p", "eyebrow", t("service.region")));
		header.append(make("span", "demo-label", t("service.catalogueDemo")));
		const language = window.LifeGraphI18n?.language;
		target.append(header, make("h2", "detail-title", window.LifeGraphI18n?.serviceName(service) || service.name));
		if (language === "ta") {
			target.append(make("p", "translation-warning", t("service.translationUnverified")));
			target.append(make("p", "service-purpose-source", `${t("service.serviceNameSource")} ${service.name}`));
		}
		target.append(make("p", "service-purpose", window.LifeGraphI18n?.servicePurpose(service) || service.purpose));
		if (language === "ta") {
			target.append(make("p", "translation-warning", t("service.purposeTranslationNote")));
		}

		const source = make("a", "source-link", t("service.openSource"));
		source.href = service.source_url;
		source.target = "_blank";
		source.rel = "noopener noreferrer";
		target.append(source);
		target.append(make("p", "verified-date", t("service.lastVerified", {
			date: service.last_verified || t("service.notVerified"),
		})));
		renderChecklist(service, target);

		const checklistLink = make("a", "button button-primary checklist-link", t("service.openChecklist"));
		checklistLink.href = `/checklist?service=${encodeURIComponent(service.id)}`;
		target.append(checklistLink);
	};

	const selectService = (service) => {
		selectedService = service;
		try {
			localStorage.setItem(selectedKey, service.id);
		} catch {
			showFeedback("service.feedbackSelectionStorage");
		}
		const params = new URLSearchParams(window.location.search);
		params.set("service", service.id);
		window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
		if (serviceRoot) renderServices(services, search?.value || "");
		renderDetails(service);
	};

	const renderServices = (items, query = "", emptyMessageKey = "service.noMatches") => {
		const list = document.querySelector("[data-service-list]");
		const count = document.querySelector("[data-service-count]");
		if (!list) return;
		list.replaceChildren();
		const normalizedQuery = query.trim().toLocaleLowerCase();
		const filteredItems = items.filter((service) => {
			const translatedName = window.LifeGraphI18n?.serviceName(service) || service.name;
			return `${service.name} ${translatedName}`.toLocaleLowerCase().includes(normalizedQuery);
		});
		if (count) count.textContent = `(${filteredItems.length})`;
		if (!filteredItems.length) {
			list.append(make("p", "empty-state", t(emptyMessageKey)));
			return;
		}
		for (const service of filteredItems) {
			const button = make("button", "service-option");
			button.type = "button";
			button.setAttribute("aria-pressed", String(selectedService?.id === service.id));
			button.append(make("strong", "", window.LifeGraphI18n?.serviceName(service) || service.name));
			if (window.LifeGraphI18n?.language === "ta") {
				button.append(make("small", "service-original-name", service.name));
				button.append(make("small", "", t("service.translationUnverified")));
			} else {
				button.append(make("small", "", t("service.needsVerification")));
			}
			button.addEventListener("click", () => selectService(service));
			list.append(button);
		}
	};

	const loadServices = async (query = "") => {
		showFeedback("service.feedbackLoading");
		try {
			const response = await fetch("/api/services");
			const payload = await response.json();
			if (!response.ok) throw new Error(t("service.feedbackError"));
			services = payload.services;
			serviceLoadError = false;
			showFeedback("service.feedbackCatalogue");
			if (serviceRoot) {
				renderServices(services, query);
				const current = services.find((item) => item.id === selectedService?.id);
				if (current) renderDetails(current);
			}
			return services;
		} catch {
			serviceLoadError = true;
			showFeedback("service.feedbackError");
			if (serviceRoot) renderServices([], "", "service.feedbackError");
			return [];
		}
	};

	if (serviceRoot) {
		search?.addEventListener("input", () => {
			renderServices(
				services,
				search.value,
				serviceLoadError ? "service.feedbackError" : "service.noMatches"
			);
		});
	}

	window.addEventListener("lifegraph:languagechange", () => {
		showFeedback(feedbackKey);
		if (serviceRoot) {
			renderServices(
				services,
				search?.value || "",
				serviceLoadError ? "service.feedbackError" : "service.noMatches"
			);
		}
		if (selectedService) renderDetails(selectedService);
		else if (checklistRoot) renderEmptyChecklist();
	});

	loadServices().then((items) => {
		if (checklistRoot) {
			const params = new URLSearchParams(window.location.search);
			let preferredId = params.get("service");
			if (!preferredId) {
				try { preferredId = localStorage.getItem(selectedKey); } catch { preferredId = null; }
			}
			const selected = items.find((service) => service.id === preferredId);
			if (selected) {
				selectedService = selected;
				renderDetails(selected);
			} else {
				renderEmptyChecklist();
			}
		} else {
			let preferredId = new URLSearchParams(window.location.search).get("service");
			if (!preferredId) {
				try { preferredId = localStorage.getItem(selectedKey); } catch { preferredId = null; }
			}
			const selected = items.find((service) => service.id === preferredId);
			if (selected) selectService(selected);
		}
	});
}
