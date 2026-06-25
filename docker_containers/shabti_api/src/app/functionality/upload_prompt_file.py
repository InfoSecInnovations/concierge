from fastapi import UploadFile
import aiofiles
from shabti_types import TempFileInfo
from .opensearch import set_temp_file


async def upload_prompt_file(file: UploadFile) -> TempFileInfo:
    async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as fp:
        binary = await file.read()
        await fp.write(binary)
        id = set_temp_file(fp.name)
    return TempFileInfo(id=id)
