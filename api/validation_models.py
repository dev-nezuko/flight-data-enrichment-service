from pydantic import BaseModel
from datetime import datetime
from typing import List


# Pydantic models for input validation
class FlightLeg(BaseModel):
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    flight_number: str
    aircraft_type: str
    cabin_type: str
    duration: int
    layover_time: float
    distance: int


class FlightData(BaseModel):
    id: str
    travel_class: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    flight_numbers: List[str]
    legs: List[FlightLeg]
    last_seen: datetime

