from __future__ import annotations
import argparse
from dataclasses import dataclass
from collections.abc import Callable

@dataclass
class InstallArgument:
    @dataclass
    class ArgumentInput:
        default: str | Callable[[ArgumentProcessor], str]
        prompt: str | None = None
        options: list[str] | None = None
        
    key: str
    help: str
    description: list[str]
    input: ArgumentInput
    condition: Callable[[ArgumentProcessor], bool] | None = None

class ArgumentProcessor:
    def __init__(self, install_arguments: list[InstallArgument]) -> None:
        self.install_arguments = install_arguments
        self.install_parameters: dict[str, str] = {}

    def __get_argument_input(self, input_data: InstallArgument.ArgumentInput):
        input_text = ""
        if callable(input_data.default):
            input_default = input_data.default(self)
        else:
            input_default = input_data.default
        if input_data.prompt:
            input_text += input_data.prompt + " "
        if input_data.options:
            input_text += " or ".join([f"[{input_option}]" if input_option == input_default else input_option for input_option in input_data.options])
        else: 
            input_text += f"[{input_default}]"
        input_text += ": "
        return input(input_text)

    def init_args(self):
        parser = argparse.ArgumentParser()
        for argument in self.install_arguments:
            parser.add_argument(f"--{argument.key}", help=argument.help)
        args = parser.parse_args()
        for argument in self.install_arguments:
            value = getattr(args, argument.key)
            if value:
                self.install_parameters[argument.key] = value

    def prompt_for_parameters(self):
        for index, argument in enumerate(self.install_arguments):
            print(f"Question {index + 1} of {len(self.install_arguments)}:")
            if argument.key in self.install_parameters:
                print("Answer provided by command line argument.")
                continue
            for line in argument.description:
                print(line)
            self.install_parameters[argument.key] = self.__get_argument_input(argument.input)
            print("\n")