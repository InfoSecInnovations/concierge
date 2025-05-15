import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core'
import * as zxcvbnCommonPackage from '@zxcvbn-ts/language-common'
import * as zxcvbnEnPackage from '@zxcvbn-ts/language-en'
import { keycloakExists } from './dockerItemsExist'
const options = {
  translations: zxcvbnEnPackage.translations,
  graphs: zxcvbnCommonPackage.adjacencyGraphs,
  dictionary: {
    ...zxcvbnCommonPackage.dictionary,
    ...zxcvbnEnPackage.dictionary,
  },
}

zxcvbnOptions.setOptions(options)

export default (formData: FormData) => {
    const securityLevel = formData.get("security_level")?.toString()
    if (!securityLevel || securityLevel == "none") return true // if you don't have security enabled Shabti will install fine with no options set
    // if keycloak will be installed, we need a valid password
    if (!keycloakExists()) {
      const keycloakPassword = formData.get("keycloak_password")?.toString()
      if (!keycloakPassword || zxcvbn(keycloakPassword).score < 4) return false
    }
    return true
}