import platform
from typing import List, Optional

import usb.core
import usb.util
from usb.backend import libusb1

from .constants import (
    GS_CAN_FEATURE_BT_CONST_EXT,
    GS_CAN_FEATURE_FD,
    GS_CAN_FEATURE_GET_STATE,
    GS_CAN_FLAG_FD,
    GS_CAN_MODE_FD,
    GS_CAN_MODE_HW_TIMESTAMP,
    GS_CAN_MODE_LISTEN_ONLY,
    GS_CAN_MODE_LOOP_BACK,
    GS_CAN_MODE_NORMAL,
    GS_CAN_MODE_ONE_SHOT,
)
from .gs_usb_frame import GsUsbFrame
from .gs_usb_structures import (
    DeviceBitTiming,
    DeviceCapability,
    DeviceInfo,
    DeviceMode,
    DeviceState,
)

# gs_usb VIDs/PIDs (devices currently in the linux kernel driver)
GS_USB_ID_VENDOR = 0x1D50
GS_USB_ID_PRODUCT = 0x606F

GS_USB_CANDLELIGHT_VENDOR_ID = 0x1209
GS_USB_CANDLELIGHT_PRODUCT_ID = 0x2323

GS_USB_CES_CANEXT_FD_VENDOR_ID = 0x1CD2
GS_USB_CES_CANEXT_FD_PRODUCT_ID = 0x606F

GS_USB_ABE_CANDEBUGGER_FD_VENDOR_ID = 0x16D0
GS_USB_ABE_CANDEBUGGER_FD_PRODUCT_ID = 0x10B8

# gs_usb mode
GS_CAN_MODE_RESET = 0
GS_CAN_MODE_START = 1

# gs_usb control request
_GS_USB_BREQ_HOST_FORMAT = 0
_GS_USB_BREQ_BITTIMING = 1
_GS_USB_BREQ_MODE = 2
_GS_USB_BREQ_BERR = 3
_GS_USB_BREQ_BT_CONST = 4
_GS_USB_BREQ_DEVICE_CONFIG = 5
_GS_USB_BREQ_TIMESTAMP = 6
_GS_USB_BREQ_IDENTIFY = 7
_GS_USB_BREQ_GET_USER_ID = 8
_GS_USB_BREQ_SET_USER_ID = 9
_GS_USB_BREQ_DATA_BITTIMING = 10
_GS_USB_BREQ_BT_CONST_EXT = 11
_GS_USB_BREQ_SET_TERMINATION = 12
_GS_USB_BREQ_GET_TERMINATION = 13
_GS_USB_BREQ_GET_STATE = 14


class GsUsb:
    def __init__(self, gs_usb):
        self.gs_usb = gs_usb
        self.capability: Optional[DeviceCapability] = None
        self.device_flags: int = 0
        self.fd_mode: bool = False

    def start(self, flags=(GS_CAN_MODE_NORMAL | GS_CAN_MODE_HW_TIMESTAMP)):
        r"""
        Start gs_usb device
        :param flags: GS_CAN_MODE_LISTEN_ONLY, GS_CAN_MODE_HW_TIMESTAMP, etc.
        """
        # Reset to support restart multiple times
        self.gs_usb.reset()

        # Detach usb from kernel driver in Linux/Unix system to perform IO
        if (
            "windows" not in platform.system().lower()
            and self.gs_usb.is_kernel_driver_active(0)
        ):
            self.gs_usb.detach_kernel_driver(0)

        # Only allow features that the device supports
        flags &= self.device_capability.feature

        # Only allow features that this driver supports
        flags &= (
            GS_CAN_MODE_LISTEN_ONLY
            | GS_CAN_MODE_LOOP_BACK
            | GS_CAN_MODE_ONE_SHOT
            | GS_CAN_MODE_HW_TIMESTAMP
            | GS_CAN_MODE_FD
        )
        self.device_flags = flags
        self.fd_mode = (flags & GS_CAN_MODE_FD) == GS_CAN_MODE_FD

        mode = DeviceMode(GS_CAN_MODE_START, flags)
        self.gs_usb.ctrl_transfer(0x41, _GS_USB_BREQ_MODE, 0, 0, mode.pack())

    def stop(self):
        r"""
        Stop gs_usb device
        """
        mode = DeviceMode(GS_CAN_MODE_RESET, 0)
        try:
            self.gs_usb.ctrl_transfer(0x41, _GS_USB_BREQ_MODE, 0, 0, mode.pack())
        except usb.core.USBError:
            pass

    def set_bitrate(self, bitrate, sample_point=87.5):
        r"""
        Set bitrate with sample point 87.5% and clock rate 48MHz.
        Ported from https://github.com/HubertD/cangaroo/blob/b4a9d6d8db7fe649444d835a76dbae5f7d82c12f/src/driver/CandleApiDriver/CandleApiInterface.cpp#L17-L112

        It can also be calculated in http://www.bittiming.can-wiki.info/ with sample point 87.5% and clock rate 48MHz
        """
        prop_seg = 1
        sjw = 1

        if (self.device_capability.fclk_can == 48000000) and (sample_point == 87.5):
            if bitrate == 10000:
                self.set_timing(prop_seg, 12, 2, sjw, 300)
            elif bitrate == 20000:
                self.set_timing(prop_seg, 12, 2, sjw, 150)
            elif bitrate == 50000:
                self.set_timing(prop_seg, 12, 2, sjw, 60)
            elif bitrate == 83333:
                self.set_timing(prop_seg, 12, 2, sjw, 36)
            elif bitrate == 100000:
                self.set_timing(prop_seg, 12, 2, sjw, 30)
            elif bitrate == 125000:
                self.set_timing(prop_seg, 12, 2, sjw, 24)
            elif bitrate == 250000:
                self.set_timing(prop_seg, 12, 2, sjw, 12)
            elif bitrate == 500000:
                self.set_timing(prop_seg, 12, 2, sjw, 6)
            elif bitrate == 800000:
                self.set_timing(prop_seg, 11, 2, sjw, 4)
            elif bitrate == 1000000:
                self.set_timing(prop_seg, 12, 2, sjw, 3)
            else:
                return False
            return True
        elif (self.device_capability.fclk_can == 80000000) and (sample_point == 87.5):
            if bitrate == 10000:
                self.set_timing(prop_seg, 12, 2, sjw, 500)
            elif bitrate == 20000:
                self.set_timing(prop_seg, 12, 2, sjw, 250)
            elif bitrate == 50000:
                self.set_timing(prop_seg, 12, 2, sjw, 100)
            elif bitrate == 83333:
                self.set_timing(prop_seg, 12, 2, sjw, 60)
            elif bitrate == 100000:
                self.set_timing(prop_seg, 12, 2, sjw, 50)
            elif bitrate == 125000:
                self.set_timing(prop_seg, 12, 2, sjw, 40)
            elif bitrate == 250000:
                self.set_timing(prop_seg, 12, 2, sjw, 20)
            elif bitrate == 500000:
                self.set_timing(prop_seg, 12, 2, sjw, 10)
            elif bitrate == 800000:
                self.set_timing(prop_seg, 7, 1, sjw, 10)
            elif bitrate == 1000000:
                self.set_timing(prop_seg, 12, 2, sjw, 5)
            else:
                return False
            return True
        elif (self.device_capability.fclk_can == 40000000) and (sample_point == 87.5):
            # CF3 / TCAN4550 uses 40MHz clock
            # Total TQ = 16 (1 sync + 1 prop + 12 phase1 + 2 phase2) for 87.5% sample point
            # brp = 40000000 / (bitrate * 16)
            if bitrate == 10000:
                self.set_timing(prop_seg, 12, 2, sjw, 250)
            elif bitrate == 20000:
                self.set_timing(prop_seg, 12, 2, sjw, 125)
            elif bitrate == 50000:
                self.set_timing(prop_seg, 12, 2, sjw, 50)
            elif bitrate == 83333:
                self.set_timing(prop_seg, 12, 2, sjw, 30)
            elif bitrate == 100000:
                self.set_timing(prop_seg, 12, 2, sjw, 25)
            elif bitrate == 125000:
                self.set_timing(prop_seg, 12, 2, sjw, 20)
            elif bitrate == 250000:
                self.set_timing(prop_seg, 12, 2, sjw, 10)
            elif bitrate == 500000:
                self.set_timing(prop_seg, 12, 2, sjw, 5)
            elif bitrate == 800000:
                # 800k doesn't divide evenly into 16 TQ, use 10 TQ (90% sample point)
                self.set_timing(prop_seg, 7, 1, sjw, 5)
            elif bitrate == 1000000:
                # 1M uses 8 TQ (87.5% sample point): 1+1+5+1=8, sample=(1+1+5)/8=87.5%
                self.set_timing(prop_seg, 5, 1, sjw, 5)
            else:
                return False
            return True

        else:
            # device clk or sample point currently unsupported
            return False

    def set_timing(self, prop_seg, phase_seg1, phase_seg2, sjw, brp):
        r"""
        Set CAN bit timing (nominal/arbitration phase)
        :param prop_seg: propagation Segment (const 1)
        :param phase_seg1: phase segment 1 (1~15)
        :param phase_seg2: phase segment 2 (1~8)
        :param sjw: synchronization segment (1~4)
        :param brp: prescaler for quantum where base_clk = 48MHz (1~1024)
        """
        bit_timing = DeviceBitTiming(prop_seg, phase_seg1, phase_seg2, sjw, brp)
        self.gs_usb.ctrl_transfer(0x41, _GS_USB_BREQ_BITTIMING, 0, 0, bit_timing.pack())

    def set_data_timing(self, prop_seg, phase_seg1, phase_seg2, sjw, brp):
        r"""
        Set CAN FD data phase bit timing
        :param prop_seg: propagation Segment (const 1)
        :param phase_seg1: phase segment 1
        :param phase_seg2: phase segment 2
        :param sjw: synchronization jump width
        :param brp: prescaler for quantum
        """
        bit_timing = DeviceBitTiming(prop_seg, phase_seg1, phase_seg2, sjw, brp)
        self.gs_usb.ctrl_transfer(
            0x41, _GS_USB_BREQ_DATA_BITTIMING, 0, 0, bit_timing.pack()
        )

    def set_data_bitrate(self, bitrate, sample_point=75.0):
        r"""
        Set CAN FD data phase bitrate.
        Common data bitrates: 2000000 (2 Mbps), 5000000 (5 Mbps), 8000000 (8 Mbps)

        :param bitrate: Data phase bitrate in bps
        :param sample_point: Sample point percentage (default 75% for high-speed data phase)
        :return: True if successful, False if unsupported
        """
        # Check if device supports CAN FD
        if not (self.device_capability.feature & GS_CAN_FEATURE_FD):
            return False

        prop_seg = 1
        sjw = 1

        # For CAN FD data phase, we typically use shorter bit times
        # Sample point is usually 70-80% for data phase
        if self.device_capability.fclk_can == 80000000:
            # 80 MHz clock (common for CAN FD devices)
            if bitrate == 2000000:
                # 80MHz / 2Mbps = 40 TQ, use 8 TQ: 1+1+4+2=8, sample=75%
                self.set_data_timing(prop_seg, 4, 2, sjw, 5)
            elif bitrate == 4000000:
                # 80MHz / 4Mbps = 20 TQ, use 4 TQ: 1+1+1+1=4, sample=75%
                self.set_data_timing(prop_seg, 1, 1, sjw, 5)
            elif bitrate == 5000000:
                # 80MHz / 5Mbps = 16 TQ, use 8 TQ: 1+1+4+2=8, sample=75%
                self.set_data_timing(prop_seg, 4, 2, sjw, 2)
            elif bitrate == 8000000:
                # 80MHz / 8Mbps = 10 TQ, use 5 TQ: 1+1+2+1=5, sample=80%
                self.set_data_timing(prop_seg, 2, 1, sjw, 2)
            else:
                return False
            return True
        elif self.device_capability.fclk_can == 40000000:
            # 40 MHz clock (TCAN4550/CF3)
            if bitrate == 2000000:
                # 40MHz / 2Mbps = 20 TQ, use 10 TQ: 1+1+6+2=10, sample=80%
                self.set_data_timing(prop_seg, 6, 2, sjw, 2)
            elif bitrate == 4000000:
                # 40MHz / 4Mbps = 10 TQ, use 5 TQ: 1+1+2+1=5, sample=80%
                self.set_data_timing(prop_seg, 2, 1, sjw, 2)
            elif bitrate == 5000000:
                # 40MHz / 5Mbps = 8 TQ, use 8 TQ: 1+1+4+2=8, sample=75%
                self.set_data_timing(prop_seg, 4, 2, sjw, 1)
            elif bitrate == 8000000:
                # 40MHz / 8Mbps = 5 TQ, use 5 TQ: 1+1+2+1=5, sample=80%
                self.set_data_timing(prop_seg, 2, 1, sjw, 1)
            elif bitrate == 10000000:
                # 40MHz / 10Mbps = 4 TQ, use 4 TQ: 1+1+1+1=4, sample=75%
                self.set_data_timing(prop_seg, 1, 1, sjw, 1)
            else:
                return False
            return True
        else:
            # Unsupported clock frequency for data phase
            return False

    def send(self, frame):
        r"""
        Send frame
        :param frame: GsUsbFrame
        """
        # Frame size is different depending on HW timestamp and FD mode
        hw_timestamps = (
            self.device_flags & GS_CAN_MODE_HW_TIMESTAMP
        ) == GS_CAN_MODE_HW_TIMESTAMP
        self.gs_usb.write(0x02, frame.pack(hw_timestamps, self.fd_mode))
        return True

    def read(self, frame, timeout_ms):
        r"""
        Read frame
        :param frame: GsUsbFrame
        :param timeout_ms: read time out in ms.
                           Note that timeout as 0 will block forever if no message is received
        :return: return True if success else False
        """
        hw_timestamps = (
            self.device_flags & GS_CAN_MODE_HW_TIMESTAMP
        ) == GS_CAN_MODE_HW_TIMESTAMP

        # In FD mode, we request the max frame size but may receive smaller frames
        # (classic CAN frames are still possible, e.g., echo frames)
        max_size = frame.__sizeof__(hw_timestamps, self.fd_mode)

        try:
            data = self.gs_usb.read(0x81, max_size, timeout_ms)
        except usb.core.USBError:
            return False

        # Determine if this is an FD frame by checking the flags byte (offset 10)
        # or by the received data length
        if len(data) >= 11:
            frame_flags = data[10]
            is_fd_frame = bool(frame_flags & GS_CAN_FLAG_FD)
        else:
            is_fd_frame = False

        GsUsbFrame.unpack_into(frame, data, hw_timestamps, is_fd_frame)
        return True

    @property
    def bus(self):
        return self.gs_usb.bus

    @property
    def address(self):
        return self.gs_usb.address

    @property
    def serial_number(self):
        r"""
        Get gs_usb device serial number in string format
        """
        return self.gs_usb.serial_number

    @property
    def device_info(self):
        r"""
        Get gs_usb device info
        """
        data = self.gs_usb.ctrl_transfer(0xC1, _GS_USB_BREQ_DEVICE_CONFIG, 0, 0, 12)
        return DeviceInfo.unpack(data)

    @property
    def device_capability(self):
        r"""
        Get gs_usb device capability
        """
        if self.capability is None:
            data = self.gs_usb.ctrl_transfer(0xC1, _GS_USB_BREQ_BT_CONST, 0, 0, 40)
            self.capability = DeviceCapability.unpack(data)
        return self.capability

    @property
    def device_capability_extended(self):
        r"""
        Get gs_usb extended device capability (includes CAN FD timing constraints)
        Returns None if device doesn't support BT_CONST_EXT
        """
        # Check if device supports extended capability
        if not (self.device_capability.feature & GS_CAN_FEATURE_BT_CONST_EXT):
            return None
        # If we already have extended capability cached, return it
        if self.capability is not None and self.capability.has_fd_timing:
            return self.capability
        # Fetch extended capability and replace the basic one
        data = self.gs_usb.ctrl_transfer(0xC1, _GS_USB_BREQ_BT_CONST_EXT, 0, 0, 72)
        self.capability = DeviceCapability.unpack_extended(data)
        return self.capability

    @property
    def supports_fd(self):
        r"""
        Check if device supports CAN FD
        """
        return (self.device_capability.feature & GS_CAN_FEATURE_FD) != 0

    @property
    def supports_get_state(self):
        r"""
        Check if device supports GET_STATE request
        """
        return (self.device_capability.feature & GS_CAN_FEATURE_GET_STATE) != 0

    def get_state(self, channel: int = 0) -> DeviceState:
        r"""
        Get CAN bus state and error counters.

        :param channel: CAN channel number (default 0)
        :return: DeviceState with state enum and error counters
        :raises: ValueError if device doesn't support GET_STATE
        """
        if not self.supports_get_state:
            raise ValueError("Device does not support GET_STATE")
        data = self.gs_usb.ctrl_transfer(0xC1, _GS_USB_BREQ_GET_STATE, channel, 0, 12)
        return DeviceState.unpack(data)

    def __str__(self):
        try:
            _ = "{} ({})".format(self.gs_usb.product, repr(self.gs_usb))
        except (ValueError, usb.core.USBError):
            return ""
        return _

    is_gs_usb_device = staticmethod(
        lambda dev: (
            dev.idVendor == GS_USB_ID_VENDOR and dev.idProduct == GS_USB_ID_PRODUCT
        )
        or (
            dev.idVendor == GS_USB_CANDLELIGHT_VENDOR_ID
            and dev.idProduct == GS_USB_CANDLELIGHT_PRODUCT_ID
        )
        or (
            dev.idVendor == GS_USB_CES_CANEXT_FD_VENDOR_ID
            and dev.idProduct == GS_USB_CES_CANEXT_FD_PRODUCT_ID
        )
        or (
            dev.idVendor == GS_USB_ABE_CANDEBUGGER_FD_VENDOR_ID
            and dev.idProduct == GS_USB_ABE_CANDEBUGGER_FD_PRODUCT_ID
        )
    )

    @classmethod
    def scan(cls) -> List["GsUsb"]:
        r"""
        Retrieve the list of gs_usb devices handle
        :return: list of gs_usb devices handle
        """
        devices = usb.core.find(
            find_all=True,
            custom_match=cls.is_gs_usb_device,
            backend=libusb1.get_backend(),
        )
        if devices is None:
            return []
        return [GsUsb(dev) for dev in devices]

    @classmethod
    def find(cls, bus, address):
        r"""
        Find a specific gs_usb device
        :return: The gs_usb device handle if found, else None
        """
        gs_usb = usb.core.find(
            custom_match=cls.is_gs_usb_device,
            bus=bus,
            address=address,
            backend=libusb1.get_backend(),
        )
        if gs_usb:
            return GsUsb(gs_usb)
        return None
