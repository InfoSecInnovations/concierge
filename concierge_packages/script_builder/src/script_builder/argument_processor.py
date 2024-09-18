from __future__ import annotations
import argparse
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any
from enum import Enum

# These are all accepted ways to answer a yes/no question, not case sensitive.
bool_mapping = {True: ["Yes", "Y", "True"], False: ["No", "N", "False"]}


@dataclass
class ArgumentData:
    # exception to handle user input that doesn't match a valid value
    class InvalidValueError(Exception):
        def __init__(self, message):
            self.message = message

    # different types of value that can be handled
    OutputType = Enum("OutputType", ["string", "bool", "int"])
    # the dictionary key used by this argument in the parameters dictionary
    key: str
    # help displayed for the command line arguments
    help: str
    # information displayed when asking the user to input the value in the interactive questionnaire
    description: list[str]
    # optional function to check if the question is relevant to the current context
    condition: Callable[[ArgumentProcessor], bool] | None = None
    # the type of the value that will be stored in the parameters dictionary
    output_type: OutputType = OutputType.string
    # optional default value, can be a function
    default: Any | Callable[[ArgumentProcessor], Any] | None = None
    # the prompt displayed at the user input
    prompt: str | None = None
    # optional list of values to constrain the answer, with bool output type this is ignored
    options: list[Any] | None = None
    # for string values we can define whether we should check against the exact casing or not
    case_sensitive: bool = True

    # convert a string supplied by the user to a valid value our program can use
    def process_value(self, input_value: str):
        if self.output_type == ArgumentData.OutputType.bool:
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
            raise ArgumentData.InvalidValueError("Please answer Yes or No!")
        elif self.output_type == ArgumentData.OutputType.int:
            try:
                value = int(input_value)
            except ValueError:
                raise ArgumentData.InvalidValueError(
                    "Please enter a valid integer number"
                )
            if self.options and input_value not in self.options:
                raise ArgumentData.InvalidValueError(
                    "Please enter a value matching one of the options!"
                )
            return value
        else:
            if not self.case_sensitive:
                if self.options and input_value.lower() not in [
                    option.lower() for option in self.options
                ]:
                    raise ArgumentData.InvalidValueError(
                        "Please enter a value matching one of the options!"
                    )
                return input_value
            if self.options and (input_value not in self.options):
                raise ArgumentData.InvalidValueError(
                    "Please enter a value matching one of the options!"
                )
            return input_value

    # convert a value used by our program to a string so the user knows what to input to reproduce the result
    def value_to_string(self, input_value: Any):
        if self.output_type == ArgumentData.OutputType.bool:
            if input_value:
                return bool_mapping[True][0]
            else:
                return bool_mapping[False][0]
        elif self.output_type == ArgumentData.OutputType.int:
            return str(input_value)
        return input_value


class ArgumentProcessor:
    def __init__(self, arguments: list[ArgumentData]) -> None:
        self.arguments = arguments
        self.parameters: dict[str, Any] = {}

    # display a prompt to the user and return a valid value from their input
    def __get_argument_input(self, input_data: ArgumentData):
        input_text = ""
        if callable(input_data.default):
            input_default = input_data.default(self)
        else:
            input_default = input_data.default
        if input_data.prompt:
            input_text += input_data.prompt + " "
        # bools are always limited to True or False as options
        if input_data.output_type == ArgumentData.OutputType.bool:
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
        # this pattern is the equivalent of a do while loop
        valid = False
        while not valid:
            value = input(input_text).strip() or input_default
            try:
                value = input_data.process_value(value)
                valid = True
            # we keep prompting the user until they enter a valid value
            except ArgumentData.InvalidValueError as e:
                print(e.message)
        return value

    # add command line values to the result, this should be called before prompting for user input
    def init_args(self):
        parser = argparse.ArgumentParser()
        for argument in self.arguments:
            parser.add_argument(f"--{argument.key}", help=argument.help)
        args = parser.parse_args()
        for argument in self.arguments:
            value = getattr(args, argument.key)
            if value:
                try:
                    self.parameters[argument.key] = argument.process_value(value)
                except ArgumentData.InvalidValueError as e:
                    print(
                        f"invalid value {value} was supplied for --{argument.key}: {e.message}"
                    )
                    print(
                        "You will be prompted to supply this value during installation."
                    )

    # iterate through the questions processing user input for each one
    def prompt_for_parameters(self):
        for index, argument in enumerate(self.arguments):
            # we still tell the user about the step even if it will be skipped so they don't get confused by the numbering
            print(f"Question {index + 1} of {len(self.arguments)}:")
            # if a condition was set it must evaluate to true for the user to be asked the question
            if argument.condition and not argument.condition(self):
                print("Question not relevant to current situation, skipping.")
                # to avoid any potential for errors, we'll remove the value if it's not relevant to the current install
                if argument.key in self.parameters:
                    del self.parameters[argument.key]
                continue
            if argument.key in self.parameters:
                print("Answer provided by command line argument.")
                continue
            for line in argument.description:
                print(line)
            self.parameters[argument.key] = self.__get_argument_input(argument)
            print("\n")

    # the command line arguments to append to the script to be able to rerun without completing the questionnaire again
    def get_command_parameters(self):
        return " ".join(
            [
                f"--{argument.key}={argument.value_to_string(self.parameters[argument.key])}"
                for argument in self.arguments
                if argument.key in self.parameters
            ]
        )
