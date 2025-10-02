from pydantic import BaseModel


class Answer(BaseModel):
    word: str
    tag: str
    description: str
