from struct import pack, unpack

from .constants import (
    CAN_EFF_FLAG,
    CAN_EFF_MASK,
    CAN_ERR_FLAG,
    CAN_RTR_FLAG,
    CANFD_DLC_TO_LEN,
    CANFD_MAX_DLEN,
    GS_CAN_FLAG_BRS,
    GS_CAN_FLAG_FD,
)

# gs_usb general
GS_USB_ECHO_ID = 0
GS_USB_NONE_ECHO_ID = 0xFFFFFFFF

# Classic CAN frame sizes
GS_USB_FRAME_SIZE = 20
GS_USB_FRAME_SIZE_HW_TIMESTAMP = 24

# CAN FD frame sizes (header + 64 bytes data)
GS_USB_FRAME_SIZE_FD = 76
GS_USB_FRAME_SIZE_FD_HW_TIMESTAMP = 80


def dlc_to_len(dlc: int, fd: bool = False) -> int:
    """Convert DLC to data length."""
    if fd:
        if dlc < len(CANFD_DLC_TO_LEN):
            return CANFD_DLC_TO_LEN[dlc]
        return CANFD_MAX_DLEN
    else:
        return min(dlc, 8)


def len_to_dlc(length: int, fd: bool = False) -> int:
    """Convert data length to DLC."""
    if fd:
        for dlc, dlen in enumerate(CANFD_DLC_TO_LEN):
            if dlen >= length:
                return dlc
        return 15  # Max DLC for CAN FD
    else:
        return min(length, 8)


class GsUsbFrame:
    def __init__(self, can_id=0, data=None, fd=False, brs=False):
        """
        Create a CAN frame.

        :param can_id: CAN identifier (with flags like CAN_EFF_FLAG if needed)
        :param data: Frame data (bytes or list of ints)
        :param fd: True for CAN FD frame (allows up to 64 bytes)
        :param brs: True for Bit Rate Switch (CAN FD only, transmit data at higher rate)
        """
        self.echo_id = GS_USB_ECHO_ID
        self.can_id = can_id
        self.channel = 0
        self.flags = 0
        self.reserved = 0
        self.timestamp_us = 0

        if data is None:
            data = []

        if isinstance(data, bytes):
            data = list(data)

        # Set frame flags
        if fd:
            self.flags |= GS_CAN_FLAG_FD
            max_len = CANFD_MAX_DLEN
        else:
            max_len = 8

        if brs and fd:
            self.flags |= GS_CAN_FLAG_BRS

        # Pad data to appropriate size
        data_len = min(len(data), max_len)
        self.data = list(data[:data_len]) + [0] * (max_len - data_len)
        self.can_dlc = len_to_dlc(len(data), fd)

    @property
    def arbitration_id(self) -> int:
        return self.can_id & CAN_EFF_MASK

    @property
    def is_extended_id(self) -> bool:
        return bool(self.can_id & CAN_EFF_FLAG)

    @property
    def is_remote_frame(self) -> bool:
        return bool(self.can_id & CAN_RTR_FLAG)

    @property
    def is_error_frame(self) -> bool:
        return bool(self.can_id & CAN_ERR_FLAG)

    @property
    def is_fd(self) -> bool:
        return bool(self.flags & GS_CAN_FLAG_FD)

    @property
    def is_brs(self) -> bool:
        return bool(self.flags & GS_CAN_FLAG_BRS)

    @property
    def timestamp(self):
        return self.timestamp_us / 1000000.0

    @property
    def data_length(self) -> int:
        """Return actual data length based on DLC and frame type."""
        return dlc_to_len(self.can_dlc, self.is_fd)

    def __sizeof__(self, hw_timestamp=False, fd_mode=False):
        """Return frame size in bytes."""
        if fd_mode:
            if hw_timestamp:
                return GS_USB_FRAME_SIZE_FD_HW_TIMESTAMP
            else:
                return GS_USB_FRAME_SIZE_FD
        else:
            if hw_timestamp:
                return GS_USB_FRAME_SIZE_HW_TIMESTAMP
            else:
                return GS_USB_FRAME_SIZE

    def __str__(self) -> str:
        fd_indicator = " FD" if self.is_fd else ""
        brs_indicator = " BRS" if self.is_brs else ""
        data = (
            "remote request"
            if self.is_remote_frame
            else " ".join("{:02X}".format(b) for b in self.data[: self.data_length])
        )
        return "{: >8X}{}{}   [{}]  {}".format(
            self.arbitration_id, fd_indicator, brs_indicator, self.data_length, data
        )

    def pack(self, hw_timestamp=False, fd_mode=False):
        """
        Pack frame into bytes for transmission.

        :param hw_timestamp: Include timestamp field
        :param fd_mode: Use CAN FD frame format (64-byte data)
        """
        if fd_mode:
            # CAN FD frame: 12-byte header + 64-byte data + optional 4-byte timestamp
            if hw_timestamp:
                return pack(
                    "<2I4B64BI",
                    self.echo_id,
                    self.can_id,
                    self.can_dlc,
                    self.channel,
                    self.flags,
                    self.reserved,
                    *self.data[:64],
                    self.timestamp_us & 0xFFFFFFFF,
                )
            else:
                return pack(
                    "<2I4B64B",
                    self.echo_id,
                    self.can_id,
                    self.can_dlc,
                    self.channel,
                    self.flags,
                    self.reserved,
                    *self.data[:64],
                )
        else:
            # Classic CAN frame: 12-byte header + 8-byte data + optional 4-byte timestamp
            if hw_timestamp:
                return pack(
                    "<2I4B8BI",
                    self.echo_id,
                    self.can_id,
                    self.can_dlc,
                    self.channel,
                    self.flags,
                    self.reserved,
                    *self.data[:8],
                    self.timestamp_us & 0xFFFFFFFF,
                )
            else:
                return pack(
                    "<2I4B8B",
                    self.echo_id,
                    self.can_id,
                    self.can_dlc,
                    self.channel,
                    self.flags,
                    self.reserved,
                    *self.data[:8],
                )

    @staticmethod
    def unpack_into(frame, data: bytes, hw_timestamp=False, fd_mode=False):
        """
        Unpack received bytes into an existing frame object.

        :param frame: GsUsbFrame object to populate
        :param data: Raw bytes received from device
        :param hw_timestamp: Data includes timestamp field
        :param fd_mode: CAN FD frame format (64-byte data)
        """
        if fd_mode:
            if hw_timestamp:
                unpacked = unpack("<2I4B64BI", data)
                (
                    frame.echo_id,
                    frame.can_id,
                    frame.can_dlc,
                    frame.channel,
                    frame.flags,
                    frame.reserved,
                ) = unpacked[:6]
                frame.data = list(unpacked[6:70])
                frame.timestamp_us = unpacked[70]
            else:
                unpacked = unpack("<2I4B64B", data)
                (
                    frame.echo_id,
                    frame.can_id,
                    frame.can_dlc,
                    frame.channel,
                    frame.flags,
                    frame.reserved,
                ) = unpacked[:6]
                frame.data = list(unpacked[6:70])
        else:
            if hw_timestamp:
                unpacked = unpack("<2I4B8BI", data)
                (
                    frame.echo_id,
                    frame.can_id,
                    frame.can_dlc,
                    frame.channel,
                    frame.flags,
                    frame.reserved,
                ) = unpacked[:6]
                frame.data = list(unpacked[6:14]) + [0] * 56
                frame.timestamp_us = unpacked[14]
            else:
                unpacked = unpack("<2I4B8B", data)
                (
                    frame.echo_id,
                    frame.can_id,
                    frame.can_dlc,
                    frame.channel,
                    frame.flags,
                    frame.reserved,
                ) = unpacked[:6]
                frame.data = list(unpacked[6:14]) + [0] * 56

    @classmethod
    def from_bytes(cls, data: bytes, hw_timestamp=False, fd_mode=False):
        """
        Create a new frame from received bytes.

        :param data: Raw bytes received from device
        :param hw_timestamp: Data includes timestamp field
        :param fd_mode: CAN FD frame format (64-byte data)
        :return: New GsUsbFrame object
        """
        frame = cls()
        cls.unpack_into(frame, data, hw_timestamp, fd_mode)
        return frame
