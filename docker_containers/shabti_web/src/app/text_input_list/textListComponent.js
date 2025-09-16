class TextInputListBinding extends Shiny.InputBinding {
	// Find element to render in
	find(scope) {
		return $(scope).find(".shiny-text-list-output");
	}

	addInput(el) {
		const input = document.createElement("input");
		input.className = "list-input";
		el.appendChild(input);
	}

	initialize(el) {
		this.addInput(el);
		return [];
	}

	getValue(el) {
		const inputs = [...$(el).find("input")];
		const emptyInputs = inputs.filter((input) => !input.value);
		if (emptyInputs.length > 1)
			emptyInputs.slice(1).forEach((el) => $(el).remove());
		if (!emptyInputs.length) this.addInput(el);
		return inputs.map((input) => input.value).filter((value) => value);
	}

	subscribe(el, callback) {
		$(el).on("input", (e) => {
			callback();
		});
	}
}

// Register the binding
Shiny.inputBindings.register(
	new TextInputListBinding(),
	"shiny-text-list-output",
);
