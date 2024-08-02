from script_builder.argument_processor import ArgumentData, ArgumentProcessor
import sys


def get_key_1(processor: ArgumentProcessor):
    return processor.parameters["key_1"]


def yes(processor: ArgumentProcessor):
    return True


def no(processor: ArgumentProcessor):
    return False


arguments = [
    ArgumentData(
        key="key_1",
        help="Help 1",
        description=["Description 1"],
        input=ArgumentData.InputData(
            default="default1",
            options=["default1", "non_default"],  # options list
        ),
    ),
    ArgumentData(
        key="key_2",
        help="Help 2",
        description=["Description 2"],
        input=ArgumentData.InputData(
            default="default2",
            prompt="prompt2?",  # prompt
        ),
    ),
    ArgumentData(
        key="key_3",
        help="Help 3",
        description=["Description 3", "This one has 2 lines"],
        input=ArgumentData.InputData(
            default=get_key_1,  # default from function
            prompt="what is key 1?",
        ),
    ),
    ArgumentData(
        key="key_4",
        help="Help 4",
        description=["Description 4"],
        condition=yes,
        input=ArgumentData.InputData(default="default4", prompt="prompt4?"),
    ),
    ArgumentData(
        key="key_5",
        help="Help 5",
        description=["Description 5"],
        condition=no,
        input=ArgumentData.InputData(default="default5", prompt="prompt5?"),
    ),
]


inputs = ["default1", "testing", "", "blah"]


def test_input_prompt():
    processor = ArgumentProcessor(arguments)
    input_parameters = processor._ArgumentProcessor__get_argument_input_parameters(
        arguments[0].input
    )
    assert (
        input_parameters.text == "[default1] or non_default: "
    )  # check that options lists are joined by "or"
    input_parameters = processor._ArgumentProcessor__get_argument_input_parameters(
        arguments[1].input
    )
    assert input_parameters.text == "prompt2? [default2]: "
    processor.parameters["key_1"] = "testing"
    input_parameters = processor._ArgumentProcessor__get_argument_input_parameters(
        arguments[2].input
    )
    assert input_parameters.text == "what is key 1? [testing]: "


def test_user_input(monkeypatch):
    processor = ArgumentProcessor(arguments)
    mock_input = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _: next(mock_input))
    processor.init_args()
    processor.prompt_for_parameters()
    assert processor.parameters["key_1"] == "default1"
    assert processor.parameters["key_2"] == "testing"
    assert (
        processor.parameters["key_3"] == processor.parameters["key_1"]
    )  # check that the default function in key_3 works
    assert (
        "key_4" in processor.parameters
    )  # check that key_4 was included because the condition returned true
    assert (
        "key_5" not in processor.parameters
    )  # check that key_5 was excluded because the condition returned false


def test_command_line(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            sys.argv[0],
            "--key_1",
            "default1",
            "--key_2",
            "testing",
            "--key_3",
            "response3",
        ],
    )
    processor = ArgumentProcessor(arguments)
    processor.init_args()
    assert processor.parameters["key_1"] == "default1"
    assert processor.parameters["key_2"] == "testing"
    assert processor.parameters["key_3"] == "response3"


partial_inputs = ["testing", "foo"]


def test_mixed_inputs(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            sys.argv[0],
            "--key_1",
            "default1",
            "--key_4",
            "bar",
        ],
    )
    processor = ArgumentProcessor(arguments)
    mock_input = iter(partial_inputs)
    monkeypatch.setattr("builtins.input", lambda _: next(mock_input))
    processor.init_args()
    processor.prompt_for_parameters()
    assert processor.parameters["key_1"] == "default1"
    assert processor.parameters["key_2"] == "testing"
    assert processor.parameters["key_3"] == "foo"
    assert processor.parameters["key_4"] == "bar"
