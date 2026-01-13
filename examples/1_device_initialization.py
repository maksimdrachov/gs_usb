"""
Device Configuration Example

This script demonstrates the full device initialization cycle for a gs_usb device,
following the protocol flow described in the gs_usb specification:

1. HOST_FORMAT (0) - Set byte order (legacy)
2. DEVICE_CONFIG (5) - Get device capabilities (channels, firmware/hardware version)
3. BT_CONST (4) - Get bit timing constraints
4. BT_CONST_EXT (11) - Get CAN FD constraints (if supported)
"""

from struct import pack, unpack

import usb.core

from gs_usb.constants import GS_CAN_FEATURE_BT_CONST_EXT
from gs_usb.gs_usb import (
    _GS_USB_BREQ_BT_CONST_EXT,
    _GS_USB_BREQ_HOST_FORMAT,
    GsUsb,
)


def send_host_format(dev):
    """
    Send HOST_FORMAT request to set byte order (legacy requirement).
    This is the first step in the initialization sequence.
    """
    print("=== Step 1: HOST_FORMAT ===")
    # Host format structure: just a 32-bit value indicating byte order
    # 0x0000beef is the magic value for little-endian
    host_format = pack("<I", 0x0000BEEF)
    try:
        dev.gs_usb.ctrl_transfer(0x41, _GS_USB_BREQ_HOST_FORMAT, 0, 0, host_format)
        print("HOST_FORMAT sent successfully (little-endian byte order)")
    except usb.core.USBError as e:
        print(f"HOST_FORMAT failed (may be optional on this device): {e}")
    print()


def get_device_config(dev):
    """
    Get device configuration including channel count and version info.
    """
    print("=== Step 2: DEVICE_CONFIG ===")
    device_info = dev.device_info

    print(
        f"Number of CAN channels: {device_info.icount + 1} (icount={device_info.icount})"
    )
    print(
        f"Firmware version: {device_info.fw_version / 10.0} (raw={device_info.fw_version})"
    )
    print(
        f"Hardware version: {device_info.hw_version / 10.0} (raw={device_info.hw_version})"
    )
    print()
    return device_info


def get_bt_const(dev):
    """
    Get bit timing constraints for nominal (arbitration) phase.
    """
    print("=== Step 3: BT_CONST (Bit Timing Constraints) ===")
    capability = dev.device_capability

    print(f"Feature bitfield: 0x{capability.feature:08x}")
    print(
        f"Clock frequency: {capability.fclk_can / 1_000_000:.1f} MHz ({capability.fclk_can} Hz)"
    )
    print(f"TSEG1 range: {capability.tseg1_min} - {capability.tseg1_max}")
    print(f"TSEG2 range: {capability.tseg2_min} - {capability.tseg2_max}")
    print(f"SJW max: {capability.sjw_max}")
    print(
        f"BRP range: {capability.brp_min} - {capability.brp_max} (increment: {capability.brp_inc})"
    )
    print()

    # Decode feature flags
    print("Supported features:")
    feature_names = [
        (0, "LISTEN_ONLY"),
        (1, "LOOP_BACK"),
        (2, "TRIPLE_SAMPLE"),
        (3, "ONE_SHOT"),
        (4, "HW_TIMESTAMP"),
        (5, "IDENTIFY"),
        (6, "USER_ID"),
        (7, "PAD_PKTS_TO_MAX_PKT_SIZE"),
        (8, "FD (CAN FD)"),
        (9, "REQ_USB_QUIRK_LPC546XX"),
        (10, "BT_CONST_EXT"),
        (11, "TERMINATION"),
        (12, "BERR_REPORTING"),
        (13, "GET_STATE"),
    ]
    for bit, name in feature_names:
        if capability.feature & (1 << bit):
            print(f"  - {name}")
    print()

    return capability


def get_bt_const_ext(dev, capability):
    """
    Get extended bit timing constraints for CAN FD data phase (if supported).
    """
    print("=== Step 4: BT_CONST_EXT (CAN FD Timing Constraints) ===")

    if not (capability.feature & GS_CAN_FEATURE_BT_CONST_EXT):
        print("BT_CONST_EXT not supported by this device (no CAN FD)")
        print()
        return None

    try:
        # BT_CONST_EXT returns extended timing info (48 bytes)
        # struct gs_device_bt_const_extended {
        #     __le32 feature;
        #     __le32 fclk_can;
        #     __le32 tseg1_min, tseg1_max;
        #     __le32 tseg2_min, tseg2_max;
        #     __le32 sjw_max;
        #     __le32 brp_min, brp_max, brp_inc;
        #     __le32 dtseg1_min, dtseg1_max;
        #     __le32 dtseg2_min, dtseg2_max;
        #     __le32 dsjw_max;
        #     __le32 dbrp_min, dbrp_max, dbrp_inc;
        # }
        data = dev.gs_usb.ctrl_transfer(0xC1, _GS_USB_BREQ_BT_CONST_EXT, 0, 0, 72)
        unpacked = unpack("<18I", data)

        print("CAN FD Data Phase Timing Constraints:")
        print(f"  DTSEG1 range: {unpacked[10]} - {unpacked[11]}")
        print(f"  DTSEG2 range: {unpacked[12]} - {unpacked[13]}")
        print(f"  DSJW max: {unpacked[14]}")
        print(
            f"  DBRP range: {unpacked[15]} - {unpacked[16]} (increment: {unpacked[17]})"
        )
        print()
        return unpacked
    except usb.core.USBError as e:
        print(f"BT_CONST_EXT request failed: {e}")
        print()
        return None


def main():
    # Find our device
    print("Scanning for gs_usb devices...")
    devs = GsUsb.scan()
    if len(devs) == 0:
        print("Can not find gs_usb device")
        return
    dev = devs[0]
    print(f"Found device: {dev}")
    print()

    # Step 1: Send HOST_FORMAT (set byte order)
    send_host_format(dev)

    # Step 2: Get device configuration
    device_info = get_device_config(dev)

    # Step 3: Get bit timing constraints
    capability = get_bt_const(dev)

    # Step 4: Get extended bit timing constraints (CAN FD) if supported
    bt_const_ext = get_bt_const_ext(dev, capability)

    print("=" * 50)
    print("Device initialization cycle complete!")
    print(f"Device has {device_info.icount + 1} CAN channel(s)")
    if bt_const_ext is not None:
        print("CAN FD is supported (BT_CONST_EXT available)")
    else:
        print("Classic CAN only (no CAN FD)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
