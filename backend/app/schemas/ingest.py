from pydantic import BaseModel, field_validator


class IngestRequest(BaseModel):
    year: int
    month: int

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("month must be between 1 and 12")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if not 2019 <= v <= 2026:
            raise ValueError("year must be between 2019 and 2026")
        return v


class IngestResponse(BaseModel):
    status: str
    row_count: int
    duration_seconds: float
    data_month: str


class IngestStatusResponse(BaseModel):
    status: str          # pending | success | error | not_found
    row_count: int | None = None
    error_msg: str | None = None
    data_month: str | None = None
