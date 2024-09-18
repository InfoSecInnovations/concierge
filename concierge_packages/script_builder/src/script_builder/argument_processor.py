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

        class InvalidValueError(Exception):
            def __init__(self, message):
                self.message = message

        def process_value(self, input_value: str):
            if self.output_type == ArgumentData.InputData.OutputType.bool:
                if (
                    input_value in [True, False]
                ):  # if we used the default value we already have a bool and we can skip the extra steps
                    return input_value
                elif input_value.lower() in [
                    option.lower() for option in bool_mapping[True]
                ]:
                    return True
                elif input_value.lower() in [
                    option.lower() for option in bool_mapping[False]
                ]:
                    return False
                raise ArgumentData.InputData.InvalidValueError(
                    "Please answer Yes or No!"
                )
            elif self.output_type == ArgumentData.InputData.OutputType.int:
                try:
                    value = int(input_value)
                except ValueError:
                    raise ArgumentData.InputData.InvalidValueError(
                        "Please enter a valid integer number"
                    )
                if self.options and input_value not in self.options:
                    raise ArgumentData.InputData.InvalidValueError(
                        "Please enter a value matching one of the options!"
                    )
                return value
            else:
                if not self.case_sensitive:
                    if self.options and input_value.lower() not in [
                        option.lower() for option in self.options
                    ]:
                        raise ArgumentData.InputData.InvalidValueError(
                            "Please enter a value matching one of the options!"
                        )
                    return input_value
                if self.options and (input_value not in self.options):
                    raise ArgumentData.InputData.InvalidValueError(
                        "Please enter a value matching one of the options!"
                    )
                return input_value

        def value_to_string(self, input_value: Any):
            if self.output_type == ArgumentData.InputData.OutputType.bool:
                if input_value:
                    return bool_mapping[True][0]
                else:
                    return bool_mapping[False][0]
            elif self.output_type == ArgumentData.InputData.OutputType.int:
                return str(input_value)
            return input_value

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
            try:
                value = input_data.process_value(value)
                valid = True
            except ArgumentData.InputData.InvalidValueError as e:
                print(e.message)
        return value

    def init_args(self):
        parser = argparse.ArgumentParser()
        for argument in self.arguments:
            parser.add_argument(f"--{argument.key}", help=argument.help)
        args = parser.parse_args()
        for argument in self.arguments:
            value = getattr(args, argument.key)
            if value:
                try:
                    self.parameters[argument.key] = argument.input.process_value(value)
                except ArgumentData.InputData.InvalidValueError as e:
                    print(
                        f"invalid value {value} was supplied for --{argument.key}: {e.message}"
                    )
                    print(
                        "You will be prompted to supply this value during installation."
                    )

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
        return " ".join(
            [
                f"--{argument.key}={argument.input.value_to_string(self.parameters[argument.key])}"
                for argument in self.arguments
            ]
        )
