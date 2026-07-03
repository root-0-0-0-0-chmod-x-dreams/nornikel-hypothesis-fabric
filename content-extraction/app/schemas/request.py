from pydantic import BaseModel, Field, HttpUrl


class ExtractRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target URL to render and extract")
