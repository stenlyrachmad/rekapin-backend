from pydantic import BaseModel, Field
from typing import Optional

class SummarizeRequest(BaseModel):
    transcript_id: Optional[str] = Field(None, description="ID of additional stored transcript")
    text: Optional[str] = Field(None, description="Direct text to summarize")
