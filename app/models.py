from pydantic import BaseModel
from typing import Optional

class SummarizeRequest(BaseModel):
    transcript_id: Optional[str] = None
    text: Optional[str] = None
