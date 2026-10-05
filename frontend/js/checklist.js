const serviceRoot = document.querySelector("[data-service-app]");
const checklistRoot = document.querySelector("[data-checklist-app]");

if (serviceRoot || checklistRoot) {
	const selectedKey = "lifegraph.selectedServiceId";
	const progressKey = "lifegraph.checklistProgress";
	const requirementProgressKey = "lifegraph.requirementChecklistProgress";
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

	const make = (tag, className, text) => {
		const element = document.createElement(tag);
		if (className) element.className = className;
		if (text !== undefined) element.textContent = text;
		return element;
	};

	const selectChecklistService = (service) => {
		selectedService = service;
		try {
			localStorage.setItem(selectedKey, service.id);
		} catch {
			showFeedback("service.feedbackSelectionStorage");
		}
		const params = new URLSearchParams(window.location.search);
		params.set("service", service.id);
		window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
		renderDetails(service);
	};

	const renderEmptyChecklist = () => {
		if (!detail) return;
		detail.replaceChildren();
		if (serviceLoadError || !services.length) {
			detail.append(make("p", "empty-state", t("service.feedbackError")));
			return;
		}

		detail.append(make("h2", "detail-title", t("checklist.chooseService")));
		detail.append(make("p", "service-purpose", t("checklist.chooseServiceHelp")));
		const choices = make("div", "checklist-service-options");
		for (const service of services) {
			const button = make("button", "service-option");
			button.type = "button";
			button.append(make("strong", "", window.LifeGraphI18n?.serviceName(service) || service.name));
			button.append(make("small", "", t("service.needsVerification")));
			button.addEventListener("click", () => selectChecklistService(service));
			choices.append(button);
		}
		detail.append(choices);
	};

	const readProgress = (key = progressKey) => {
		try {
			const stored = JSON.parse(localStorage.getItem(key) || "{}");
			if (stored && typeof stored === "object" && !Array.isArray(stored)) return stored;
			showFeedback("service.feedbackStorage");
			return {};
		} catch {
			showFeedback("service.feedbackStorage");
			return {};
		}
	};

	const saveChecklistState = (key, serviceId, index, checked) => {
		try {
			const progress = readProgress(key);
			const state = Array.isArray(progress[serviceId]) ? progress[serviceId] : [];
			state[index] = checked;
			progress[serviceId] = state;
			localStorage.setItem(key, JSON.stringify(progress));
		} catch {
			showFeedback("service.feedbackStorage");
		}
	};

	const renderChecklist = (service, target) => {
		const requirementsPanel = make("section", "checklist-section");
		requirementsPanel.append(make("h3", "detail-section-title", t("service.requirementsHeading")));
		const requirementsVerified = service.verification_status === "verified"
			&& service.requirements.length > 0;
		const statusKey = requirementsVerified
			? "service.verified"
			: "service.needsVerification";
		requirementsPanel.append(make("span", "verification-badge", t(statusKey)));
		if (!requirementsVerified) {
			requirementsPanel.append(make(
				"p",
				"verification-message",
				service.requirements.length
					? t("service.requirementItemsUnverified")
					: t("service.requirementsUnverified")
			));
		}
		if (service.requirements.length) {
			if (window.LifeGraphI18n?.language === "ta") {
				requirementsPanel.append(make("p", "verification-message", t("service.requirementTranslationNote")));
			}
			const savedRequirements = readProgress(requirementProgressKey)[service.id] || [];
			const progressLabel = make("p", "progress-label");
			const progress = make("progress", "checklist-progress");
			progress.max = service.requirements.length;
			progress.setAttribute("aria-label", t("service.requirementProgressLabel"));
			const updateRequirementProgress = () => {
				const done = service.requirements.reduce(
					(count, _, index) => count + (savedRequirements[index] ? 1 : 0),
					0
				);
				progressLabel.textContent = t("service.requirementProgress", {
					done,
					total: service.requirements.length,
				});
				progress.value = done;
			};
			requirementsPanel.append(progressLabel, progress);

			const requirementList = make("div", "reminder-list requirement-checklist");
			service.requirements.forEach((requirement, index) => {
				const label = make("label", "reminder-item");
				const input = document.createElement("input");
				input.type = "checkbox";
				input.checked = Boolean(savedRequirements[index]);
				input.setAttribute("aria-label", requirement);
				input.addEventListener("change", () => {
					savedRequirements[index] = input.checked;
					saveChecklistState(requirementProgressKey, service.id, index, input.checked);
					updateRequirementProgress();
				});
				label.append(input, make("span", "", requirement));
				requirementList.append(label);
			});
			updateRequirementProgress();
			requirementsPanel.append(requirementList);
		} else {
			requirementsPanel.append(make("p", "empty-requirements", t("service.noProofItems")));
		}
		target.append(requirementsPanel);

		const reminderPanel = make("section", "checklist-section reminder-section");
		const heading = make("div", "reminder-heading");
		heading.append(make("h3", "detail-section-title", t("service.remindersHeading")));
		heading.append(make("span", "demo-label", t("service.demoNotRequirements")));
		reminderPanel.append(heading);
		reminderPanel.append(make("p", "reminder-caption", t("service.reminderDescription")));

		const saved = readProgress(progressKey)[service.id] || [];
		const progressLabel = make("p", "progress-label");
		const progress = make("progress", "checklist-progress");
		progress.max = reminderKeys.length;
		progress.setAttribute("aria-label", t("service.progressLabel"));
		const updateReminderProgress = () => {
			const doneCount = reminderKeys.reduce(
				(count, _, index) => count + (saved[index] ? 1 : 0),
				0
			);
			progressLabel.textContent = t("service.reminderProgress", {
				done: doneCount,
				total: reminderKeys.length,
			});
			progress.value = doneCount;
		};
		updateReminderProgress();
		reminderPanel.append(progressLabel, progress);

		const list = make("div", "reminder-list");
		reminderKeys.forEach((reminderKey, index) => {
			const label = make("label", "reminder-item");
			const input = document.createElement("input");
			input.type = "checkbox";
			input.setAttribute("aria-label", t(reminderKey));
			input.checked = Boolean(saved[index]);
			input.addEventListener("change", () => {
				saved[index] = input.checked;
				saveChecklistState(progressKey, service.id, index, input.checked);
				updateReminderProgress();
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

		if (serviceRoot) {
			const checklistLink = make("a", "button button-primary checklist-link", t("service.openChecklist"));
			checklistLink.href = `/checklist?service=${encodeURIComponent(service.id)}`;
			target.append(checklistLink);
		}
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
				try {
					preferredId = localStorage.getItem(selectedKey);
				} catch {
					preferredId = null;
					showFeedback("service.feedbackSelectionStorage");
				}
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
				try {
					preferredId = localStorage.getItem(selectedKey);
				} catch {
					preferredId = null;
					showFeedback("service.feedbackSelectionStorage");
				}
			}
			const selected = items.find((service) => service.id === preferredId);
			if (selected) selectService(selected);
		}
	});
}
