from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from api.utils import make_aware

AirportCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class FlightLeg(BaseModel):
    origin: AirportCode
    destination: AirportCode
    departure_time: datetime
    arrival_time: datetime
    flight_number: str
    aircraft_type: str
    cabin_type: str
    duration: int = Field(ge=0)
    layover_time: float = Field(ge=0)
    distance: int = Field(ge=0)


class FlightData(BaseModel):
    id: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    travel_class: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    origin: AirportCode
    destination: AirportCode
    departure_time: datetime
    arrival_time: datetime
    flight_numbers: list[str]
    legs: list[FlightLeg]
    last_seen: datetime

    @model_validator(mode="after")
    def arrival_not_before_departure(self):
        if make_aware(self.arrival_time) < make_aware(self.departure_time):
            raise ValueError("arrival_time must not be before departure_time")
        return self
