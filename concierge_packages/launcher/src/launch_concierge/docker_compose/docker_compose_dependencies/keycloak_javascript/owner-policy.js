var permission = $evaluation.getPermission()
var resource = permission.getResource()
var owner = resource.getOwner()
var context = $evaluation.getContext()
var identity = context.getIdentity()
var id = identity.getId()

if (owner == id) {
    $evaluation.grant()
}