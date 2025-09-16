class TextInputListBinding extends Shiny.InputBinding {
	// Find element to render in
	find(scope) {
		return $(scope).find(".shiny-text-list-output");
	}

	initialize(el) {
		const input = document.createElement("input");
		input.className = "listInput";
		el.appendChild(input);
		return [];
	}

	getValue(el) {
		return [...$(el).find("input")].map((el) => el.value);
	}

	subscribe(el, callback) {
		$(el).on("input", "input", (e) => {
			callback();
		});
	}
}

// Register the binding
Shiny.inputBindings.register(
	new TextInputListBinding(),
	"shiny-text-list-output",
);
