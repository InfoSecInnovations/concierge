var permission = $evaluation.getPermission();
var resource = permission.getResource();
var shabtiOwner =
	resource.getAttribute("shabti_owner") &&
	resource.getAttribute("shabti_owner")[0];
var context = $evaluation.getContext();
var identity = context.getIdentity();
var id = identity.getId();

if (shabtiOwner && id && shabtiOwner == id) {
	$evaluation.grant();
}
