from pydantic import BaseModel, Field


class EndgameAttemptRequest(BaseModel):
    move_uci: str = Field(min_length=4, max_length=8)
    grade: str = Field(pattern="^(again|hard|good|easy)$")
