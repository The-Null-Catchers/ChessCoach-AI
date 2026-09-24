from pydantic import BaseModel, Field


class RepertoireCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    color: str = Field(pattern="^(white|black)$")
    description: str | None = Field(default=None, max_length=2000)


class RepertoireImport(BaseModel):
    pgn: str = Field(min_length=1, max_length=2_000_000)


class OpeningAttemptRequest(BaseModel):
    move_uci: str = Field(min_length=4, max_length=8)
    grade: str = Field(pattern="^(again|hard|good|easy)$")
