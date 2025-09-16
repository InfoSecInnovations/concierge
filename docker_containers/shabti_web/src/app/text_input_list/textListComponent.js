class TextInputListBinding extends Shiny.InputBinding {
	// Find element to render in
	find(scope) {
		return $(scope).find(".shiny-text-list-output");
	}

	addInput(el) {
		const container = $(el).find(".list-container")[0];
		const inputContainer = document.createElement("div");
		inputContainer.className = "form-group";
		const input = document.createElement("input");
		input.className = "list-input form-control";
		inputContainer.appendChild(input);
		container.appendChild(inputContainer);
	}

	initialize(el) {
		const container = document.createElement("div");
		container.className = "list-container";
		el.appendChild(container);
		this.addInput(el);
		return [];
	}

	getValue(el) {
		const inputs = [...$(el).find(".list-input")];
		const emptyInputs = inputs.filter((input) => !input.value);
		if (emptyInputs.length > 1)
			emptyInputs.slice(1).forEach((el) => $(el).parent().remove());
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
