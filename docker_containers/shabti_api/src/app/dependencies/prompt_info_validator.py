from shabti_types import PromptInfo
from fastapi import HTTPException
from ..functionality.load_prompter_config import load_prompter_config


class PromptInfoValidator:
    async def __call__(self, prompt_info: PromptInfo):
        # TODO: validate prompt_info.model, model must exist and have chat tag
        tasks = load_prompter_config("tasks")
        if prompt_info.task not in tasks:
            raise HTTPException(status_code=400, detail="Requested task not found")
        if prompt_info.persona:
            personas = load_prompter_config("personas")
            if prompt_info.persona not in personas:
                raise HTTPException(
                    status_code=400, detail="Requested persona not found"
                )
        if prompt_info.enhancers:
            enhancers = load_prompter_config("enhancers")
            for enhancer in prompt_info.enhancers:
                if enhancer not in enhancers:
                    raise HTTPException(
                        status_code=400, detail="Requested enhancer not found"
                    )
