from script_builder.util import disallow_admin
from script_builder.argument_processor import ArgumentProcessor
from concierge_install_arguments import install_arguments

disallow_admin()

argument_processor = ArgumentProcessor(install_arguments)

argument_processor.init_args()

# message:
print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")

print("Welcome to the Concierge installer.")
print("Just a few configuration questions and then some download scripts will run.")
print("Note: you can just hit enter to accept the default option.\n\n")

argument_processor.prompt_for_parameters()

print("Concierge setup is almost complete.\n")
print("If you want to speed up the deployment of future Concierge instances with these exact options, save the command below.\n")
print("After git clone or unzipping, run this command and you can skip all these questions!\n\n")
print("\ninstall.py" + argument_processor.get_command_parameters() + "\n\n\n")
    

