from concierge_installer.arguments import install_arguments
from concierge_installer.functions import (
    init_arguments,
    clean_up_existing,
    prompt_for_parameters,
    start_install,
    finish_install,
)

argument_processor = init_arguments(install_arguments)
clean_up_existing()
prompt_for_parameters(argument_processor)
start_install(argument_processor, "production")
finish_install(argument_processor)
