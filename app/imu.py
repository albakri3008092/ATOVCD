"""Helmet orientation: real IMU when one is wired, simulated telemetry otherwise.

Selected with ``ATOVCD_IMU``:

``simulate``
    Smooth synthetic pitch/roll/yaw. Default, so the console still shows a
    plausible attitude panel on a desk with no sensor attached.
``mpu6050``
    MPU-6050 over I2C. Pitch and roll come from the accelerometer, which is an
    absolute reference; yaw is integrated from the gyro because the part has no
    magnetometer, so it drifts and is reported as ``RELATIVE``.
``bno085``
    BNO085 over I2C. The part fuses on-chip and reports an absolute quaternion,
    so yaw is a real heading.

Any sensor that cannot be opened or read degrades to the simulator instead of
taking the server down: an operator would rather lose the attitude panel than
the live picture.
"""

import logging
import math
import os
import threading
import time

log = logging.getLogger("atovcd.imu")

MODES = ("simulate", "mpu6050", "bno085")

MPU6050_ADDRESS = 0x68
MPU6050_PWR_MGMT_1 = 0x6B
MPU6050_ACCEL_XOUT_H = 0x3B
# ±2 g and ±250 °/s, the power-on ranges: a helmet turn stays well inside both.
ACCEL_SCALE = 16384.0
GYRO_SCALE = 131.0


class SimulatedIMU:
    """Deterministic sweep, driven by wall clock so it never sits still."""

    mode = "simulate"
    name = "SIMULATED"

    def read(self) -> dict:
        t = time.time()
        return {
            "status": "SIMULATED",
            "pitch": round(math.sin(t * 0.2) * 4.2, 2),
            "roll": round(math.cos(t * 0.16) * 3.1, 2),
            "yaw": round((t * 1.4) % 360.0, 2),
            "yaw_reference": "RELATIVE",
        }


class Mpu6050IMU:
    """MPU-6050 over I2C: accelerometer attitude plus an integrated yaw."""

    mode = "mpu6050"
    name = "MPU-6050"

    def __init__(self, bus_number: int = 1, address: int = MPU6050_ADDRESS) -> None:
        from smbus2 import SMBus  # imported lazily; only present on a Pi with I2C

        self._address = address
        self._bus = SMBus(bus_number)
        self._bus.write_byte_data(address, MPU6050_PWR_MGMT_1, 0x00)  # leave sleep mode
        self._lock = threading.Lock()
        self._yaw = 0.0
        self._last_read = time.monotonic()
        self.read()  # fail here, while build_imu() can still fall back
        log.info("mpu6050 ready on i2c-%d addr 0x%02x", bus_number, address)

    def read(self) -> dict:
        with self._lock:
            block = self._bus.read_i2c_block_data(self._address, MPU6050_ACCEL_XOUT_H, 14)
            now = time.monotonic()
            elapsed, self._last_read = now - self._last_read, now
            ax, ay, az = (_word(block, i) / ACCEL_SCALE for i in (0, 2, 4))
            gz = _word(block, 12) / GYRO_SCALE
            # Gravity gives an absolute tilt; yaw has no such reference on this
            # part, so it is integrated and drifts by a few degrees a minute.
            self._yaw = (self._yaw + gz * elapsed) % 360.0
            yaw = self._yaw
        return {
            "status": "LOCKED",
            "pitch": round(math.degrees(math.atan2(-ax, math.hypot(ay, az))), 2),
            "roll": round(math.degrees(math.atan2(ay, math.hypot(ax, az))), 2),
            "yaw": round(yaw, 2),
            "yaw_reference": "RELATIVE",
        }


class Bno085IMU:
    """BNO085 over I2C: on-chip fusion, so yaw is an absolute heading."""

    mode = "bno085"
    name = "BNO085"

    def __init__(self) -> None:
        import adafruit_bno08x  # imported lazily; only present with the driver
        import board
        import busio
        from adafruit_bno08x.i2c import BNO08X_I2C

        self._sensor = BNO08X_I2C(busio.I2C(board.SCL, board.SDA))
        self._sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
        self._lock = threading.Lock()
        self.read()  # fail here, while build_imu() can still fall back
        log.info("bno085 ready")

    def read(self) -> dict:
        with self._lock:
            x, y, z, w = self._sensor.quaternion
        pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
        roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return {
            "status": "LOCKED",
            "pitch": round(math.degrees(pitch), 2),
            "roll": round(math.degrees(roll), 2),
            "yaw": round(math.degrees(yaw) % 360.0, 2),
            "yaw_reference": "ABSOLUTE",
        }


class GuardedIMU:
    """Wraps a real sensor so a cable that falls out cannot stop the pipeline."""

    def __init__(self, sensor) -> None:
        self._sensor = sensor
        self._fallback = SimulatedIMU()
        self.mode = sensor.mode
        self.name = sensor.name

    def read(self) -> dict:
        try:
            return self._sensor.read()
        except Exception as exc:
            log.warning("imu read failed (%s: %s), reporting simulated attitude", type(exc).__name__, exc)
            reading = self._fallback.read()
            reading["status"] = "FAULT"
            return reading


def _word(block: list[int], offset: int) -> int:
    """Big-endian signed 16-bit sample at ``offset`` of a burst read."""
    value = (block[offset] << 8) | block[offset + 1]
    return value - 65536 if value > 32767 else value


def build_imu(mode: str = ""):
    """Return the requested IMU, degrading to the simulator instead of failing."""
    mode = mode or os.environ.get("ATOVCD_IMU", "simulate")
    if mode not in MODES:
        log.warning("unknown IMU mode %r, using simulated attitude", mode)
        return SimulatedIMU()
    if mode == "simulate":
        return SimulatedIMU()
    try:
        return GuardedIMU(Mpu6050IMU() if mode == "mpu6050" else Bno085IMU())
    except Exception as exc:
        log.warning("cannot open %s (%s: %s), using simulated attitude", mode, type(exc).__name__, exc)
        return SimulatedIMU()
