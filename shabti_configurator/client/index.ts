import { zxcvbn, zxcvbnOptions } from "@zxcvbn-ts/core";
import * as zxcvbnCommonPackage from "@zxcvbn-ts/language-common";
import * as zxcvbnEnPackage from "@zxcvbn-ts/language-en";
import {
	type VNode,
	type VNodeChildren,
	attributesModule,
	classModule,
	eventListenersModule,
	h,
	init,
	propsModule,
	styleModule,
	toVNode,
} from "snabbdom";
import TomSelect from "tom-select";
import "tom-select/dist/css/tom-select.css";

const patch = init([
	// Init patch function with chosen modules
	classModule, // makes it easy to toggle classes
	propsModule, // for setting properties on DOM elements
	styleModule, // handles styling on elements with support for animations
	eventListenersModule, // attaches event listeners
	attributesModule, // for setting attributes on DOM elements
]);

const options = {
	translations: zxcvbnEnPackage.translations,
	graphs: zxcvbnCommonPackage.adjacencyGraphs,
	dictionary: {
		...zxcvbnCommonPackage.dictionary,
		...zxcvbnEnPackage.dictionary,
	},
};

zxcvbnOptions.setOptions(options);

const password1El = document.getElementById(
	"keycloak_password_first",
) as HTMLInputElement;
const password2El = document.getElementById(
	"keycloak_password",
) as HTMLInputElement;
const formSubmitEls = document.querySelectorAll(".install_button");
const loggingEls = document.querySelectorAll(".logging_element");
const loggingToggle = document.getElementById(
	"activity_logging",
)! as HTMLInputElement;
const formEl = document.getElementById("install_form") as HTMLFormElement;
let passwordStatus: VNode = toVNode(
	document.getElementById("password_status")!,
);
let formErrors: VNode = toVNode(document.getElementById("form_errors")!);
let formSuccess: VNode = toVNode(document.getElementById("form_success")!);

const patchPassword = (contents: VNodeChildren) => {
	passwordStatus = patch(
		passwordStatus,
		h("div#password_status.error", contents),
	);
};

const patchFormErrors = (contents: VNodeChildren) => {
	formErrors = patch(formErrors, h("div#form_errors.error", contents));
};

const patchFormSuccess = (contents: VNodeChildren) => {
	formSuccess = patch(formSuccess, h("div#form_success.success", contents));
};

// the native multiple select needs ctrl-clicking and gives no indication that more than one
// option can be picked, so we replace it with a tag style widget. Tom Select keeps the original
// select in the DOM and mirrors the selection onto it, so the form submission and the
// onchange handler below carry on working as they did.
const wireMultiSelect = (selectId: string) => {
	const el = document.getElementById(selectId) as HTMLSelectElement | null;
	if (!el) return; // the section this belongs to isn't on the page
	new TomSelect(el, { plugins: ["remove_button"] });
};

// the default chat model can only be chosen when more than one model is selected, so the
// selector is rendered on the fly. Both the install form and the model management form have
// one, hence the ids being parameters, they have to be unique across the page.
const wireDefaultModelSelector = (selectId: string, containerId: string) => {
	const chatModelSelector = document.getElementById(
		selectId,
	) as HTMLSelectElement | null;
	const container = document.getElementById(containerId);
	if (!chatModelSelector || !container) return; // the section this belongs to isn't on the page
	const selectorId = `${containerId}_select`;
	let vnode: VNode = toVNode(container);
	chatModelSelector.onchange = () => {
		const selected = [...chatModelSelector.selectedOptions].map((s) => s.value);
		// keep the current choice if it's still selected, otherwise the browser would silently
		// fall back to the first option
		const previous = (
			document.getElementById(selectorId) as HTMLSelectElement | null
		)?.value;
		const options = selected.map((model) =>
			h(
				"option",
				{ attrs: { value: model, selected: model == previous } },
				model,
			),
		);
		vnode = patch(
			vnode,
			h(
				`div#${containerId}`,
				selected.length > 1
					? h("p", [
							h("label", { attrs: { for: selectorId } }, "Default Chat Model"),
							h(
								"select",
								{ attrs: { id: selectorId, name: "default_model" } },
								options,
							),
							"This model will be selected by default unless the user chooses a different one.",
						])
					: undefined,
			),
		);
	};
};

// uninstalling can't be undone, so we make the user confirm what they're about to lose. The
// warning is built here rather than server side because it depends on the checkbox state
const wireUninstallConfirmation = () => {
	const form = document.getElementById(
		"uninstall_form",
	) as HTMLFormElement | null;
	if (!form) return; // Shabti isn't configured, so there's nothing to uninstall
	form.onsubmit = (e) => {
		const deleteModels = (
			document.getElementById("delete_model_files") as HTMLInputElement | null
		)?.checked;
		const warnings = [
			"Are you sure you want to uninstall Shabti?",
			"All document collections and the documents they contain will be permanently lost.",
			...(deleteModels
				? [
						"The language model files will be deleted, and will have to be downloaded again if you install Shabti in the future.",
					]
				: []),
		];
		if (!window.confirm(warnings.join("\n\n"))) e.preventDefault();
	};
};

const enableSubmit = () =>
	formSubmitEls.forEach((el) => ((el as HTMLButtonElement).disabled = false));

const disableSubmit = () =>
	formSubmitEls.forEach((el) => ((el as HTMLButtonElement).disabled = true));

const checkPasswords = () => {
	if (!password1El || !password2El) {
		patchPassword(null);
		enableSubmit();
		return;
	}
	const password1 = password1El.value;
	const password2 = password2El.value;
	if (!password1 && !password2) {
		patchPassword(h("p", "please provide a strong password!"));
		disableSubmit();
		return;
	}
	if (password1 && !password2) {
		patchPassword(h("p", "please confirm the password!"));
		disableSubmit();
		return;
	}
	if (password1 != password2) {
		patchPassword(h("p", "passwords don't match!"));
		disableSubmit();
		return;
	}
	const strength = zxcvbn(password2);
	if (strength.score < 4) {
		patchPassword([
			h("p", "Password is too weak!"),
			strength.feedback.warning
				? h("p", `warning: ${strength.feedback.warning}`)
				: undefined,
			strength.feedback.suggestions.length ? h("p", "suggestions:") : undefined,
			...strength.feedback.suggestions.map((suggestion) => h("p", suggestion)),
		]);
		disableSubmit();
		return;
	}
	patchPassword(null);
	enableSubmit();
};

if (password2El) password2El.oninput = checkPasswords;

const setLoggingVisibility = () => {
	if (loggingToggle.checked) {
		loggingEls.forEach((el) => el.classList.remove("hidden"));
	} else {
		loggingEls.forEach((el) => el.classList.add("hidden"));
	}
};
setLoggingVisibility();
loggingToggle.onchange = setLoggingVisibility;

const setFormVisibility = () => {
	const formData = new FormData(formEl);
	const keycloakConfig = document.getElementById("keycloak_config");
	if (formData.get("security_level") != "none") {
		keycloakConfig?.classList.remove("hidden");
		checkPasswords();
	} else {
		keycloakConfig?.classList.add("hidden");
		patchPassword(null);
		enableSubmit();
	}
};
setFormVisibility();
formEl.onchange = setFormVisibility;

wireMultiSelect("language_model");
wireMultiSelect("manage_language_model");
wireDefaultModelSelector("language_model", "default_model_selector");
wireDefaultModelSelector(
	"manage_language_model",
	"manage_default_model_selector",
);
wireUninstallConfirmation();

const params = new URLSearchParams(window.location.search);
const err = params.get("err");
if (err == "invalid-form") patchFormErrors("Form data was invalid");
else if (err)
	patchFormErrors([h("p", "Error occurred during installation:"), h("p", err)]);
const success = params.get("done");
if (success) patchFormSuccess(success);
window.history.replaceState(null, "", "/"); // delete the URL params after patching the page
