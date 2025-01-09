from install_concierge.installer_lib.docker_containers import (
    keycloak_exists,
    remove_keycloak,
    opensearch_exists,
    remove_opensearch,
    concierge_exists,
    remove_concierge,
)


def destroy_instance():
    # note: we don't destroy Ollama because it takes a really long time to pull the models again and the settings are the same for all configurations.
    if keycloak_exists():
        remove_keycloak()
    if opensearch_exists():
        remove_opensearch()
    if concierge_exists():
        remove_concierge()
