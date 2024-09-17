from __future__ import annotations
import argparse
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any
from enum import Enum

bool_mapping = {True: ["Yes", "Y", "True"], False: ["No", "N", "False"]}


@dataclass
class ArgumentData:
    @dataclass
    class InputData:
        OutputType = Enum("OutputType", ["string", "bool", "int"])
        default: Any | Callable[[ArgumentProcessor], Any] | None = None
        prompt: str | None = None
        options: list[Any] | None = None
        case_sensitive: bool = True
        output_type: OutputType = OutputType.string

    key: str
    help: str
    description: list[str]
    input: InputData
    condition: Callable[[ArgumentProcessor], bool] | None = None


class ArgumentProcessor:
    def __init__(self, arguments: list[ArgumentData]) -> None:
        self.arguments = arguments
        self.parameters: dict[str, Any] = {}

    def __get_argument_input(self, input_data: ArgumentData.InputData):
        input_text = ""
        if callable(input_data.default):
            input_default = input_data.default(self)
        else:
            input_default = input_data.default
        if input_data.prompt:
            input_text += input_data.prompt + " "
        if input_data.output_type == ArgumentData.InputData.OutputType.bool:
            input_text += " or ".join(
                [
                    f"[{bool_mapping[input_option][0]}]"
                    if input_option == input_default
                    else bool_mapping[input_option][0]
                    for input_option in [True, False]
                ]
            )
        else:
            if input_data.options:
                input_text += " or ".join(
                    [
                        f"[{input_option}]"
                        if input_option == input_default
                        else input_option
                        for input_option in input_data.options
                    ]
                )
            elif input_default:
                input_text += f"[{input_default}]"
        input_text += ": "
        valid = False
        while not valid:
            value = input(input_text).strip() or input_default
            if input_data.output_type == ArgumentData.InputData.OutputType.bool:
                if (
                    value in [True, False]
                ):  # if we used the default value we already have a bool and we can skip the extra steps
                    valid = True
                elif value.lower() in [option.lower() for option in bool_mapping[True]]:
                    value = True
                    valid = True
                elif value.lower() in [
                    option.lower() for option in bool_mapping[False]
                ]:
                    value = False
                    valid = True
                if not valid:
                    print("Please answer Yes or No!")
            elif input_data.output_type == ArgumentData.InputData.OutputType.int:
                try:
                    value = int(value)
                    valid = True
                except ValueError:
                    print("Please enter a valid integer number!")
                    continue
                if input_data.options and value not in input_data.options:
                    print("Please enter a value matching one of the options!")
                    continue
                valid = True
            else:
                if not input_data.case_sensitive:
                    if input_data.options and value.lower() not in [
                        option.lower() for option in input_data.options
                    ]:
                        print("Please enter a value matching one of the options!")
                        continue
                    valid = True
                else:
                    valid = not input_data.options or (value in input_data.options)
        return value

    def init_args(self):
        parser = argparse.ArgumentParser()
        for argument in self.arguments:
            parser.add_argument(f"--{argument.key}", help=argument.help)
        args = parser.parse_args()
        for argument in self.arguments:
            value = getattr(args, argument.key)
            # TODO: map string value to typed value
            if value:
                self.parameters[argument.key] = value

    def prompt_for_parameters(self):
        for index, argument in enumerate(self.arguments):
            print(f"Question {index + 1} of {len(self.arguments)}:")
            if argument.key in self.parameters:
                print("Answer provided by command line argument.")
                continue
            for line in argument.description:
                print(line)
            self.parameters[argument.key] = self.__get_argument_input(argument.input)
            print("\n")

    def get_command_parameters(self):
        # TODO: map typed value to string
        return " " + " ".join(
            [
                f"--{argument.key}={self.parameters[argument.key]}"
                for argument in self.arguments
            ]
        )
