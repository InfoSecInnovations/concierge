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
    type VNode
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
let passwordStatus: HTMLElement | VNode = document.getElementById("password_status")!
let formErrors: HTMLElement | VNode = document.getElementById("form_errors")!

const patchPassword = (newVNode: VNode) => {
    passwordStatus = patch(passwordStatus, newVNode)
}

const patchFormErrors = (newVNode: VNode) => {
    formErrors = patch(formErrors, newVNode)
}

const enableSubmit = () => formSubmitEl.disabled = false

const disableSubmit = () => formSubmitEl.disabled = true

const checkPasswords = () => {
    const password1 = password1El.value
    const password2 = password2El.value
    if (!password1 && !password2) {
        patchPassword(h('div#password_status', h('p', "please provide a strong password!")))
        disableSubmit()
        return
    }
    if (password1 && !password2) {
        patchPassword(h('div#password_status', h('p', "please confirm the password!")))
        disableSubmit()
        return
    }
    if (password1 != password2) {
        patchPassword(h('div#password_status', h('p', "passwords don't match!")))
        disableSubmit()
        return
    }
    const strength = zxcvbn(password2)
    if (strength.score < 4) {
        patchPassword(h('div#password_status', [
            h('p', 'Password is too weak!'),
            strength.feedback.warning ? h('p', `warning: ${strength.feedback.warning}`) : undefined,
            strength.feedback.suggestions.length ? h('p', 'suggestions:') : undefined,
            ...strength.feedback.suggestions.map(suggestion => h('p', suggestion))
        ]))
        disableSubmit()
        return
    }
    patchPassword(h('div#password_status'))
    enableSubmit()
}


password2El.oninput = checkPasswords

const formEl = document.getElementById("install_form") as HTMLFormElement
const setFormVisibility = () => {
    const formData = new FormData(formEl)
    const keycloakConfig = document.getElementById("keycloak_config")
    if (formData.get("security_level") != "none") {
        keycloakConfig?.classList.remove("hidden")
        checkPasswords()
    } 
    else {
        keycloakConfig?.classList.add("hidden")
        enableSubmit()
    } 
}
setFormVisibility()
formEl.onchange = setFormVisibility

const params = new URLSearchParams(window.location.search)
const err = params.get("err")
if (err == "invalid-form") patchFormErrors(h("div#form_errors", "Form data was invalid"))