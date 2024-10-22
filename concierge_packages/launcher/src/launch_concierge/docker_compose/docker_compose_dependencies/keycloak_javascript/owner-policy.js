var permission = $evaluation.getPermission()
var resource = permission.getResource()
var conciergeOwner = resource.getAttribute("concierge_owner").asString(0)
var context = $evaluation.getContext()
var identity = context.getIdentity()
var id = identity.getId()

if (conciergeOwner == id) {
    $evaluation.grant()
}