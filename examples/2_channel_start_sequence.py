"""
Channel Start Sequence Example (CAN FD)

This script demonstrates the CAN FD channel start sequence for a gs_usb device,
following the protocol flow described in the gs_usb specification:

1. BITTIMING (1) - Set nominal bit timing (1 Mbps arbitration phase)
2. DATA_BITTIMING (10) - Set CAN FD data phase timing (5 Mbps)
3. MODE (2) - Start channel with FD + HW_TIMESTAMP flags

This example configures:
- Arbitration (nominal) bitrate: 1 Mbps
- Data bitrate: 5 Mbps
"""

import time

import usb.core

from gs_usb.constants import (
    GS_CAN_MODE_FD,
    GS_CAN_MODE_LOOP_BACK,
    GS_CAN_MODE_NORMAL,
    GS_CAN_MODE_ONE_SHOT,
)
from gs_usb.gs_usb import GsUsb
from gs_usb.gs_usb_frame import GsUsbFrame


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

    # Check device capabilities
    capability = dev.device_capability
    print(f"Device clock: {capability.fclk_can / 1_000_000:.1f} MHz")
    print(f"Feature flags: 0x{capability.feature:08x}")

    if not dev.supports_fd:
        print("ERROR: Device does not support CAN FD!")
        print("This example requires a CAN FD capable device.")
        return

    print("Device supports CAN FD")
    print()

    # Get extended capabilities for CAN FD timing info
    cap_ext = dev.device_capability_extended
    if cap_ext:
        print("=== CAN FD Timing Constraints ===")
        print(f"Data phase TSEG1: {cap_ext.dtseg1_min} - {cap_ext.dtseg1_max}")
        print(f"Data phase TSEG2: {cap_ext.dtseg2_min} - {cap_ext.dtseg2_max}")
        print(f"Data phase SJW max: {cap_ext.dsjw_max}")
        print(f"Data phase BRP: {cap_ext.dbrp_min} - {cap_ext.dbrp_max}")
        print()

    # Step 1: Set nominal (arbitration) bit timing - 1 Mbps
    print("=== Step 1: BITTIMING (Nominal Phase) ===")
    print("Setting arbitration bitrate to 1 Mbps...")
    if not dev.set_bitrate(1000000):
        print("ERROR: Failed to set nominal bitrate!")
        print("Your device clock may not be supported.")
        return
    print("Nominal bitrate set successfully")
    print()

    # Step 2: Set data phase bit timing - 5 Mbps
    print("=== Step 2: DATA_BITTIMING (Data Phase) ===")
    print("Setting data bitrate to 5 Mbps...")
    if not dev.set_data_bitrate(5000000):
        print("ERROR: Failed to set data bitrate!")
        print("Your device clock may not support 5 Mbps.")
        print("Try 2 Mbps or 4 Mbps instead.")
        return
    print("Data bitrate set successfully")
    print()

    # Step 3: Start channel with FD mode enabled
    print("=== Step 3: MODE (Start Channel) ===")
    flags = (
        GS_CAN_MODE_NORMAL
        | GS_CAN_MODE_FD
        | GS_CAN_MODE_ONE_SHOT
        | GS_CAN_MODE_LOOP_BACK
    )
    print(f"Starting channel with flags: 0x{flags:04x}")
    print("  - GS_CAN_MODE_NORMAL")
    print("  - GS_CAN_MODE_ONE_SHOT")
    print("  - GS_CAN_MODE_FD")
    dev.start(flags)
    print("Channel started successfully!")
    print()

    print("=" * 50)
    print("CAN FD Channel Start Sequence Complete!")
    print("=" * 50)
    print()
    print("Configuration:")
    print("  Arbitration bitrate: 1 Mbps")
    print("  Data bitrate: 5 Mbps")
    print("  FD mode: Enabled")
    print("  HW timestamps: Enabled")
    print()

    # Demonstrate sending a CAN FD frame
    print("=== Sending Test CAN FD Frame ===")
    # Create a CAN FD frame with 64 bytes of data (requires FD mode)
    test_data = bytes(range(64))  # 0x00, 0x01, ..., 0x17
    fd_frame = GsUsbFrame(can_id=0x123, data=test_data, fd=True, brs=True)
    print(f"TX  {fd_frame}")

    try:
        dev.send(fd_frame)
        print("Frame sent successfully!")
    except usb.core.USBError as e:
        print(f"Failed to send frame: {e}")

    print()

    # Listen for incoming frames for a few seconds
    print("=== Listening for CAN FD Frames (5 seconds) ===")
    print("(Connect to a CAN FD bus to see received frames)")
    print()

    end_time = time.time() + 5
    frame_count = 0
    echo_count = 0
    rx_count = 0
    while time.time() < end_time:
        iframe = GsUsbFrame()
        if dev.read(iframe, 100):  # 100ms timeout
            frame_count += 1
            if iframe.is_echo_frame:
                # Echo frame = TX confirmation from device (our transmitted frame)
                echo_count += 1
                print(f"ECHO  {iframe}")
            else:
                # RX frame = frame received from CAN bus
                rx_count += 1
                print(f"RX    {iframe}")

    print()
    print(f"Total frames: {frame_count} (echo: {echo_count}, rx: {rx_count})")
    print()

    # Stop the device
    print("Stopping device...")
    dev.stop()
    print("Device stopped.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        raise
