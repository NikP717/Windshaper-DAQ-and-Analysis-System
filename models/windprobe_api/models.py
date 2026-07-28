"""
Minimal probe data models for the standalone logger client.

Mirrors the subset of types from the windsuite-backend
(src.models.math_types / src.models.windprobe_models) that the
Nucleo transceiver needs, without the heavy pydantic/numpy deps.
"""

from dataclasses import dataclass
from enum import IntEnum


@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


class ProbeConversionStatus(IntEnum):
    CONVERSION_OK = 0x00
    PRESSURE_OUT_OF_RANGE = 0x01
    VELOCITY_OUT_OF_RANGE = 0x02
    ANGLE_TOO_STEEP = 0x03
    CONVERSION_FAILED = 0x04


@dataclass
class ProbeRawData:
    """Raw data from the wind probe."""

    timestamp_s: float
    windspeed_vels_mps: Vec3
    temperature_celcius: float
    atmospheric_pressure_hpascal: float
    static_pressure_pascal: float
    status_byte: ProbeConversionStatus
    crc_ok: bool
