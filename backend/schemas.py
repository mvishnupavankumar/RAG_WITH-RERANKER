from pydantic import BaseModel, Field


class CreateNotebookRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=12000)
