import logging
import struct
import threading
import time
from typing import Protocol

import serial
import serial.tools.list_ports

from .models import (
    ProbeConversionStatus,
    ProbeRawData,
    Vec3,
)

logger = logging.getLogger(__name__)

FRAME_FLOATS = 4  # uz, uy, ux, pstat_abs
FRAME_SIZE = FRAME_FLOATS * 4  # 4 floats * 4 bytes each
TAIL = b"\r\n"


class CallbackNewProbeData(Protocol):
    def __call__(self, raw_probe_data: ProbeRawData) -> None: ...


class NucleoProbeTransceiver:
    def __init__(
        self,
        probe_ready: threading.Event,
        probe_error: threading.Event,
        callback_new_probe_data: CallbackNewProbeData,
    ) -> None:
        self.probe_ready = probe_ready
        self.probe_error = probe_error
        self.serial_port: serial.Serial | None = None
        self.callback_new_probe_data = callback_new_probe_data
        self._synced = False

        self.not_found_counter = 0

    def set_serial_port(self, serial_port: serial.Serial) -> None:
        self.serial_port = serial_port
        self.serial_port.reset_input_buffer()
        self._synced = False

    def parse_data_from_probe(
        self,
        received_data: bytes,
        timestamp_s: float,
    ) -> ProbeRawData | None:
        if not received_data.endswith(TAIL):
            logger.error("Frame terminator missing from probe data: %s", received_data)
            self._synced = False
            return None

        payload = received_data[: -len(TAIL)]
        if len(payload) != FRAME_SIZE:
            logger.error("Unexpected payload size %s (expected %s)", len(payload), FRAME_SIZE)
            return None

        try:
            # uz, uy, ux, pstat_abs = struct.unpack("<" + "f" * FRAME_FLOATS, payload)
            ux, uy, uz, pstat_abs = struct.unpack("<" + "f" * FRAME_FLOATS, payload)
        except struct.error as err:
            logger.error("Failed to unpack probe payload %s", err)  # noqa: TRY400, Rationale: dumb fucking linter
            return None

        # values = (uz, uy, ux, pstat_abs)
        # if any(math.isnan(value) for value in values):
        #    logger.debug("Discarding frame containing NaN values: %s", values)
        #    return None

        return ProbeRawData(
            timestamp_s=timestamp_s,
            windspeed_vels_mps=Vec3(x=ux, y=uy, z=uz),
            temperature_celcius=0.0,
            atmospheric_pressure_hpascal=0.0,
            static_pressure_pascal=pstat_abs,
            status_byte=ProbeConversionStatus.CONVERSION_OK,
            crc_ok=True,
        )

    def reading_routine(self) -> None:
        if not self.probe_ready.is_set():
            return

        if self.serial_port is None:
            logger.error("Serial port is not opened, cannot read data from probe")
            self._signal_error()
            return

        try:
            if not self._synced:
                self._wait_for_tail()
                self._synced = True

            frame_bytes = self._read_frame_bytes()
        except TimeoutError as err:
            logger.error("Timeout while reading from probe: %s", err)  # noqa: TRY400, Rationale: dumb fucking linter
            self._signal_error()
            return
        except (serial.SerialException, OSError) as err:
            logger.error("Error reading from serial port: %s", err)  # noqa: TRY400, Rationale: dumb fucking linter
            self._signal_error()
            return
        except RuntimeError as err:
            logger.error("Serial port error: %s", err)  # noqa: TRY400, Rationale: dumb fucking linter
            return

        timestamp_s = time.time()
        parsed_data = self.parse_data_from_probe(
            received_data=frame_bytes,
            timestamp_s=timestamp_s,
        )

        if parsed_data is None:
            logger.debug("Failed to parse frame: %s", frame_bytes)
            return

        self.callback_new_probe_data(parsed_data)

    def open_probe_serial(self) -> serial.Serial | None:
        """
        Returns:
            serial.Serial: The openned serial port of the probe

        """
        # ! NUCLEO
        VID = 0x0483  # # noqa: N806
        PID = 0x374B  # # noqa: N806

        ports = serial.tools.list_ports.comports()

        # This gives a list of serial ports
        # But lists the ones not available or connected to anything as n/a
        # Only keep the ones without n/a
        ports = [port for port in ports if "n/a" not in str(port)]

        # ! Check if there is any viable com port available
        if not ports:
            if self.not_found_counter % 10 == 0:
                logger.info("No serial port found, trying again every second")
                self.not_found_counter += 1
                return None

        for port in ports:
            if port.vid == VID and port.pid == PID:
                # ? Try to open the port and send a command to check if it's a probe

                try:
                    ser = serial.Serial(port=port.device, baudrate=115200, timeout=1)
                except (serial.SerialException, OSError, PermissionError) as err:
                    logger.info("Error opening serial port {}: {}", port.device, err)
                    return None

                return ser

        return None

    def _signal_error(self) -> None:
        self.probe_ready.clear()
        self.probe_error.set()

    def _require_serial_port(self, context: str) -> serial.Serial:
        if self.serial_port is None or not self.serial_port.is_open:
            logger.error("Serial port is not open while %s", context)
            self._signal_error()
            raise RuntimeError("Serial port closed during probe communication")
        return self.serial_port

    def _wait_for_tail(self) -> None:
        serial_port = self._require_serial_port("waiting for frame terminator")

        window = bytearray()
        max_len = len(TAIL)

        while True:
            chunk = serial_port.read(1)
            if not chunk:
                time.sleep(0.01)
                continue

            window.extend(chunk)
            if len(window) > max_len:
                del window[:-max_len]

            if bytes(window) == TAIL:
                return

    def _read_frame_bytes(self) -> bytes:
        serial_port = self._require_serial_port("reading frame bytes")
        payload = self._read_exact(serial_port, FRAME_SIZE)
        tail = self._read_exact(serial_port, len(TAIL))
        return payload + tail

    def _read_exact(self, serial_port: serial.Serial, size: int) -> bytes:
        buf = bytearray()

        while len(buf) < size:
            chunk = serial_port.read(size - len(buf))
            if not chunk:
                time.sleep(0.01)
                continue

            buf.extend(chunk)

        return bytes(buf)
