from shabti_types import PromptInfo
from fastapi import HTTPException
from ..functionality.load_prompter_config import load_prompter_config
from ..functionality.models import get_models, default_model_id


class PromptInfoValidator:
    async def __call__(self, prompt_info: PromptInfo):
        chat_models = await get_models(tags=["chat"])
        if prompt_info.model_name:
            if not any(m["id"] == prompt_info.model_name for m in chat_models["data"]):
                raise HTTPException(
                    status_code=400,
                    detail="Requested model not found or not chat-enabled",
                )
        # without a requested model the prompt will fall back to the default model,
        # so we check here that there is one, as errors can't be reported once the
        # response has started streaming
        elif not default_model_id(chat_models):
            raise HTTPException(status_code=400, detail="No chat model is available")
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
