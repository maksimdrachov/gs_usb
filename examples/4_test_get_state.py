"""
Test GET_STATE Example

This script demonstrates how to retrieve the CAN bus state and error counters
using the GS_USB_BREQ_GET_STATE request.

The state information includes:
- CAN state (ERROR_ACTIVE, ERROR_WARNING, ERROR_PASSIVE, BUS_OFF, STOPPED, SLEEPING)
- RX error counter (REC)
- TX error counter (TEC)

This is useful for monitoring CAN bus health and diagnosing communication issues.
"""

import time

from gs_usb.constants import (
    GS_CAN_MODE_HW_TIMESTAMP,
    GS_CAN_MODE_LOOP_BACK,
    GS_CAN_MODE_NORMAL,
    GS_CAN_STATE_BUS_OFF,
    GS_CAN_STATE_ERROR_ACTIVE,
    GS_CAN_STATE_ERROR_PASSIVE,
    GS_CAN_STATE_ERROR_WARNING,
)
from gs_usb.gs_usb import GsUsb


def main():
    print("=" * 60)
    print("GS-USB GET_STATE Test")
    print("=" * 60)
    print()

    # Find device
    print("Scanning for gs_usb devices...")
    devs = GsUsb.scan()
    if len(devs) == 0:
        print("ERROR: No gs_usb device found")
        return 1

    dev = devs[0]
    print(f"Found device: {dev}")
    print()

    # Check device capabilities
    capability = dev.device_capability
    print(f"Device clock: {capability.fclk_can / 1_000_000:.1f} MHz")
    print(f"Feature flags: 0x{capability.feature:08x}")

    if not dev.supports_get_state:
        print()
        print("ERROR: Device does not support GET_STATE feature")
        print("This feature requires GS_CAN_FEATURE_GET_STATE (bit 13) to be set")
        return 1

    print("GET_STATE support: Yes")
    print()

    # Configure and start device
    print("-" * 60)
    print("Configuring CAN interface...")
    print("-" * 60)

    if not dev.set_bitrate(500000):
        print("ERROR: Failed to set bitrate")
        return 1
    print("Bitrate: 500 kbps")

    # Start with loopback mode (so we don't need a real bus)
    flags = GS_CAN_MODE_NORMAL | GS_CAN_MODE_HW_TIMESTAMP | GS_CAN_MODE_LOOP_BACK
    dev.start(flags)
    print("Mode: Loopback + HW Timestamp")
    print("Device started successfully")
    print()

    # Get and display state
    print("-" * 60)
    print("CAN Bus State")
    print("-" * 60)

    state = dev.get_state()

    print(f"State: {state.state_name}")
    print(f"RX Error Counter (REC): {state.rxerr}")
    print(f"TX Error Counter (TEC): {state.txerr}")
    print()

    # Explain the state
    print("State explanation:")
    if state.state == GS_CAN_STATE_ERROR_ACTIVE:
        print("  ERROR_ACTIVE: Normal operation, TEC and REC are below 96")
    elif state.state == GS_CAN_STATE_ERROR_WARNING:
        print("  ERROR_WARNING: TEC or REC exceeded 96")
    elif state.state == GS_CAN_STATE_ERROR_PASSIVE:
        print("  ERROR_PASSIVE: TEC or REC exceeded 127")
    elif state.state == GS_CAN_STATE_BUS_OFF:
        print("  BUS_OFF: TEC exceeded 255, node is off the bus")
    else:
        print(f"  {state.state_name}: Device is not actively communicating")
    print()

    # Monitor state for a few seconds
    print("-" * 60)
    print("Monitoring state for 3 seconds...")
    print("-" * 60)

    start_time = time.time()
    last_state = None
    while time.time() - start_time < 3.0:
        state = dev.get_state()

        # Only print if state changed
        state_tuple = (state.state, state.rxerr, state.txerr)
        if state_tuple != last_state:
            elapsed = time.time() - start_time
            print(
                f"[{elapsed:5.2f}s] State: {state.state_name:15} "
                f"REC: {state.rxerr:3}  TEC: {state.txerr:3}"
            )
            last_state = state_tuple

        time.sleep(0.1)

    print()
    print("Monitoring complete")
    print()

    # Stop device
    dev.stop()
    print("Device stopped")

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        exit(130)
    except Exception as e:
        print(f"Error: {e}")
        raise
