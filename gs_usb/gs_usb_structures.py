from struct import pack, unpack
from typing import Optional

from .constants import GS_CAN_STATE_NAMES


class DeviceMode:
    def __init__(self, mode, flags):
        self.mode = mode
        self.flags = flags

    def __str__(self):
        return "Mode: %u\r\nFlags: 0x%08x\r\n" % (self.mode, self.flags)

    def pack(self):
        return pack("<II", self.mode, self.flags)


class DeviceBitTiming:
    def __init__(self, prop_seg, phase_seg1, phase_seg2, sjw, brp):
        self.prop_seg = prop_seg
        self.phase_seg1 = phase_seg1
        self.phase_seg2 = phase_seg2
        self.sjw = sjw
        self.brp = brp

    def __str__(self):
        return (
            "Prop Seg: %u\r\n"
            "Phase Seg 1: %u\r\n"
            "Phase Seg 2: %u\r\n"
            "SJW: %u\r\n"
            "BRP: %u\r\n"
            % (self.prop_seg, self.phase_seg1, self.phase_seg2, self.sjw, self.brp)
        )

    def pack(self):
        return pack(
            "<5I", self.prop_seg, self.phase_seg1, self.phase_seg2, self.sjw, self.brp
        )


class DeviceInfo:
    def __init__(self, reserved1, reserved2, reserved3, icount, fw_version, hw_version):
        self.reserved1 = reserved1
        self.reserved2 = reserved2
        self.reserved3 = reserved3
        self.icount = icount
        self.fw_version = fw_version
        self.hw_version = hw_version

    def __str__(self):
        return "iCount: %u\r\nFW Version: %.1f\r\nHW Version: %.1f\r\n" % (
            self.icount,
            self.fw_version / 10.0,
            self.hw_version / 10.0,
        )

    @staticmethod
    def unpack(data: bytes):
        unpacked_data = unpack("<4B2I", data)
        return DeviceInfo(*unpacked_data)


class DeviceCapability:
    """
    Device capability including bit timing constraints.

    Supports both classic CAN (BT_CONST) and CAN FD (BT_CONST_EXT) devices.
    When created from BT_CONST_EXT data, the data phase timing fields are populated.
    """

    def __init__(
        self,
        feature: int,
        clk: int,
        tseg1_min: int,
        tseg1_max: int,
        tseg2_min: int,
        tseg2_max: int,
        sjw_max: int,
        brp_min: int,
        brp_max: int,
        brp_inc: int,
        # CAN FD data phase timing (optional)
        dtseg1_min: Optional[int] = None,
        dtseg1_max: Optional[int] = None,
        dtseg2_min: Optional[int] = None,
        dtseg2_max: Optional[int] = None,
        dsjw_max: Optional[int] = None,
        dbrp_min: Optional[int] = None,
        dbrp_max: Optional[int] = None,
        dbrp_inc: Optional[int] = None,
    ):
        # Nominal (arbitration) phase timing
        self.feature = feature
        self.fclk_can = clk
        self.tseg1_min = tseg1_min
        self.tseg1_max = tseg1_max
        self.tseg2_min = tseg2_min
        self.tseg2_max = tseg2_max
        self.sjw_max = sjw_max
        self.brp_min = brp_min
        self.brp_max = brp_max
        self.brp_inc = brp_inc
        # Data phase timing (CAN FD) - None if not available
        self.dtseg1_min = dtseg1_min
        self.dtseg1_max = dtseg1_max
        self.dtseg2_min = dtseg2_min
        self.dtseg2_max = dtseg2_max
        self.dsjw_max = dsjw_max
        self.dbrp_min = dbrp_min
        self.dbrp_max = dbrp_max
        self.dbrp_inc = dbrp_inc

    @property
    def has_fd_timing(self) -> bool:
        """Check if CAN FD data phase timing is available."""
        return self.dtseg1_min is not None

    def __str__(self):
        result = (
            "Feature bitfield: 0x%08x\r\n"
            "Clock: %u\r\n"
            "TSEG1: %u - %u\r\n"
            "TSEG2: %u - %u\r\n"
            "SJW (max): %u\r\n"
            "BRP: %u - %u\r\n"
            % (
                self.feature,
                self.fclk_can,
                self.tseg1_min,
                self.tseg1_max,
                self.tseg2_min,
                self.tseg2_max,
                self.sjw_max,
                self.brp_min,
                self.brp_max,
            )
        )
        if self.has_fd_timing:
            result += (
                "Data Phase (CAN FD):\r\n"
                "  DTSEG1: %u - %u\r\n"
                "  DTSEG2: %u - %u\r\n"
                "  DSJW (max): %u\r\n"
                "  DBRP: %u - %u\r\n"
                % (
                    self.dtseg1_min,
                    self.dtseg1_max,
                    self.dtseg2_min,
                    self.dtseg2_max,
                    self.dsjw_max,
                    self.dbrp_min,
                    self.dbrp_max,
                )
            )
        return result

    @staticmethod
    def unpack(data: bytes) -> "DeviceCapability":
        """Unpack from BT_CONST response (40 bytes, 10 x uint32)."""
        unpacked_data = unpack("<10I", data)
        return DeviceCapability(*unpacked_data)

    @staticmethod
    def unpack_extended(data: bytes) -> "DeviceCapability":
        """Unpack from BT_CONST_EXT response (72 bytes, 18 x uint32)."""
        unpacked_data = unpack("<18I", data)
        return DeviceCapability(*unpacked_data)


# Alias for backward compatibility
DeviceCapabilityExtended = DeviceCapability


class DeviceState:
    """
    CAN device state from GS_USB_BREQ_GET_STATE response.

    Contains the current CAN bus state and error counters.
    """

    def __init__(self, state: int, rxerr: int, txerr: int):
        self.state = state
        self.rxerr = rxerr
        self.txerr = txerr

    @property
    def state_name(self) -> str:
        """Get human-readable state name."""
        return GS_CAN_STATE_NAMES.get(self.state, f"UNKNOWN({self.state})")

    @property
    def is_error_active(self) -> bool:
        """Check if in normal operation (error active state)."""
        return self.state == 0

    @property
    def is_bus_off(self) -> bool:
        """Check if bus is off (TEC > 255)."""
        return self.state == 3

    def __str__(self):
        return (
            f"State: {self.state_name}\r\n"
            f"RX Error Counter: {self.rxerr}\r\n"
            f"TX Error Counter: {self.txerr}\r\n"
        )

    @staticmethod
    def unpack(data: bytes) -> "DeviceState":
        """Unpack from GET_STATE response (12 bytes, 3 x uint32)."""
        state, rxerr, txerr = unpack("<3I", data)
        return DeviceState(state, rxerr, txerr)
