import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core'
import * as zxcvbnCommonPackage from '@zxcvbn-ts/language-common'
import * as zxcvbnEnPackage from '@zxcvbn-ts/language-en'
import {
    init,
    classModule,
    propsModule,
    styleModule,
    eventListenersModule,
    h,
    attributesModule,
    toVNode,
    type VNode,
    type VNodeChildren
  } from "snabbdom";
  
const patch = init([
// Init patch function with chosen modules
classModule, // makes it easy to toggle classes
propsModule, // for setting properties on DOM elements
styleModule, // handles styling on elements with support for animations
eventListenersModule, // attaches event listeners
attributesModule // for setting attributes on DOM elements
]);

const options = {
  translations: zxcvbnEnPackage.translations,
  graphs: zxcvbnCommonPackage.adjacencyGraphs,
  dictionary: {
    ...zxcvbnCommonPackage.dictionary,
    ...zxcvbnEnPackage.dictionary,
  },
}

zxcvbnOptions.setOptions(options)

const password1El = document.getElementById("keycloak_password_first")! as HTMLInputElement
const password2El = document.getElementById("keycloak_password")! as HTMLInputElement
const formSubmitEl = document.getElementById("install_submit")! as HTMLButtonElement
const loggingEls = document.querySelectorAll(".logging_element")
const loggingToggle = document.getElementById("activity_logging")! as HTMLInputElement
const formEl = document.getElementById("install_form") as HTMLFormElement
let passwordStatus: VNode = toVNode(document.getElementById("password_status")!)
let formErrors: VNode = toVNode(document.getElementById("form_errors")!)

const patchPassword = (contents: VNodeChildren) => {
    passwordStatus = patch(passwordStatus, h('div#password_status.error', contents))
}

const patchFormErrors = (contents: VNodeChildren) => {
    formErrors = patch(formErrors, h("div#form_errors.error", contents))
}

const enableSubmit = () => formSubmitEl.disabled = false

const disableSubmit = () => formSubmitEl.disabled = true

const checkPasswords = () => {
    const password1 = password1El.value
    const password2 = password2El.value
    if (!password1 && !password2) {
        patchPassword(h('p', "please provide a strong password!"))
        disableSubmit()
        return
    }
    if (password1 && !password2) {
        patchPassword(h('p', "please confirm the password!"))
        disableSubmit()
        return
    }
    if (password1 != password2) {
        patchPassword(h('p', "passwords don't match!"))
        disableSubmit()
        return
    }
    const strength = zxcvbn(password2)
    if (strength.score < 4) {
        patchPassword([
            h('p', 'Password is too weak!'),
            strength.feedback.warning ? h('p', `warning: ${strength.feedback.warning}`) : undefined,
            strength.feedback.suggestions.length ? h('p', 'suggestions:') : undefined,
            ...strength.feedback.suggestions.map(suggestion => h('p', suggestion))
        ])
        disableSubmit()
        return
    }
    patchPassword(null)
    enableSubmit()
}


password2El.oninput = checkPasswords

const setLoggingVisibility = () => {
    if (loggingToggle.checked) {
        loggingEls.forEach(el => el.classList.remove("hidden"))
    }
    else {
        loggingEls.forEach(el => el.classList.add("hidden"))
    }
}
setLoggingVisibility()
loggingToggle.onchange = setLoggingVisibility

const setFormVisibility = () => {
    const formData = new FormData(formEl)
    const keycloakConfig = document.getElementById("keycloak_config")
    if (formData.get("security_level") != "none") {
        keycloakConfig?.classList.remove("hidden")
        checkPasswords()
    } 
    else {
        keycloakConfig?.classList.add("hidden")
        patchPassword(null)
        enableSubmit()
    } 
}
setFormVisibility()
formEl.onchange = setFormVisibility

const params = new URLSearchParams(window.location.search)
const err = params.get("err")
if (err == "invalid-form") patchFormErrors("Form data was invalid")