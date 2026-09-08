// Patches a progress toast in place. The toast is shown once and never re-rendered, so nothing
// outside the rows container - the ingest Cancel button in particular - is ever unbound and
// rebound. The rows themselves are built here because how many there are keeps changing.

function progressRow(key) {
	const row = document.createElement("div");
	row.className = "mt-2";
	row.dataset.rowKey = key;
	row.innerHTML =
		'<div class="small text-truncate" data-row-label></div>' +
		'<div class="progress" style="height: 0.5rem">' +
		'<div class="progress-bar" data-row-bar></div>' +
		"</div>" +
		'<div class="small text-muted" data-row-detail></div>';
	return row;
}

function fillProgressRow(row, spec) {
	const label = row.querySelector("[data-row-label]");
	label.textContent = spec.label || "";
	label.title = spec.label || "";
	row.querySelector("[data-row-detail]").textContent = spec.detail || "";
	const bar = row.querySelector("[data-row-bar]");
	// no number yet, but the work is definitely happening: Bootstrap's indeterminate look
	const indeterminate = spec.percent === null || spec.percent === undefined;
	bar.classList.toggle("progress-bar-striped", indeterminate);
	bar.classList.toggle("progress-bar-animated", indeterminate);
	// toggled rather than added: a row that was in progress last poll and is finished now is the
	// same node, and `add` on an empty variant throws. utility classes rather than literal colours,
	// because the theme picker can change what success and danger look like at runtime
	bar.classList.toggle("bg-success", spec.variant === "success");
	bar.classList.toggle("bg-danger", spec.variant === "danger");
	bar.style.width = indeterminate ? "100%" : `${spec.percent}%`;
}

Shiny.addCustomMessageHandler("shabtiProgress", (msg) => {
	// looked up every time rather than cached: showing a toast on an id that is already up
	// replaces the element, which would leave a held reference pointing at a detached node
	const toast = document.getElementById(msg.id);
	if (!toast) {
		return;
	}
	if (msg.status !== undefined) {
		toast.querySelector("[data-progress-status]").textContent = msg.status;
	}
	if (msg.rows === undefined) {
		return;
	}
	const container = toast.querySelector("[data-progress-rows]");
	const existing = new Map();
	for (const row of container.children) {
		existing.set(row.dataset.rowKey, row);
	}
	for (const spec of msg.rows) {
		let row = existing.get(spec.key);
		if (row) {
			existing.delete(spec.key);
		} else {
			row = progressRow(spec.key);
		}
		fillProgressRow(row, spec);
		// re-appending a node that is already in place is a no-op, so this both adds new rows and
		// keeps the order matching what the server sent
		container.appendChild(row);
	}
	// whatever the server no longer mentions has finished
	for (const row of existing.values()) {
		row.remove();
	}
});
