"""
Test All Bitrates Example

This script tests all supported Classic CAN and CAN FD bitrates by:
1. Configuring the CAN interface with loopback mode
2. Sending a test frame
3. Verifying that 2 frames are received (1 echo + 1 loopback RX) with correct payload

Classic CAN bitrates tested (40MHz clock):
- 10k, 20k, 50k, 100k, 125k, 250k, 500k, 1M

CAN FD bitrate combinations tested (40MHz clock):
- Arbitration: 125k, 250k, 500k, 1M
- Data: 2M, 5M, 8M, 10M
"""

import sys
import time

from gs_usb.constants import (
    GS_CAN_MODE_FD,
    GS_CAN_MODE_HW_TIMESTAMP,
    GS_CAN_MODE_LOOP_BACK,
    GS_CAN_MODE_NORMAL,
)
from gs_usb.gs_usb import GsUsb
from gs_usb.gs_usb_frame import GsUsbFrame

# Test configuration
TEST_CAN_ID = 0x123
TEST_DATA_CLASSIC = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE])
TEST_DATA_FD = bytes(range(64))  # 0x00 to 0x3F
READ_TIMEOUT_MS = 1000  # 1 second timeout for reading frames

# Classic CAN bitrates to test
CLASSIC_CAN_BITRATES = [
    10000,
    20000,
    50000,
    100000,
    125000,
    250000,
    500000,
    1000000,
]

# CAN FD arbitration bitrates
FD_ARBITRATION_BITRATES = [
    125000,
    250000,
    500000,
    1000000,
]

# CAN FD data bitrates
FD_DATA_BITRATES = [
    2000000,
    5000000,
    8000000,
    10000000,
]


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error_message = ""
        self.echo_received = False
        self.rx_received = False
        self.echo_data_correct = False
        self.rx_data_correct = False


def verify_frame_data(frame: GsUsbFrame, expected_data: bytes, is_fd: bool) -> bool:
    """Verify that the frame data matches expected data."""
    expected_len = len(expected_data)
    actual_data = bytes(frame.data[:expected_len])
    return actual_data == expected_data


def run_single_test(
    dev: GsUsb,
    test_name: str,
    is_fd: bool,
    expected_data: bytes,
) -> TestResult:
    """Run a single test: send frame and verify echo + loopback RX."""
    result = TestResult(test_name)

    # Create test frame
    if is_fd:
        tx_frame = GsUsbFrame(can_id=TEST_CAN_ID, data=expected_data, fd=True, brs=True)
    else:
        tx_frame = GsUsbFrame(can_id=TEST_CAN_ID, data=expected_data)

    # Send frame
    try:
        dev.send(tx_frame)
    except Exception as e:
        result.error_message = f"Failed to send frame: {e}"
        return result

    # Read frames (expecting 2: echo + loopback RX)
    frames_received = []
    start_time = time.time()
    while len(frames_received) < 2 and (time.time() - start_time) < 2.0:
        rx_frame = GsUsbFrame()
        if dev.read(rx_frame, READ_TIMEOUT_MS):
            frames_received.append(rx_frame)

    # Analyze received frames
    for frame in frames_received:
        if frame.is_echo_frame:
            result.echo_received = True
            result.echo_data_correct = verify_frame_data(frame, expected_data, is_fd)
        else:
            result.rx_received = True
            result.rx_data_correct = verify_frame_data(frame, expected_data, is_fd)

    # Determine pass/fail
    if not result.echo_received:
        result.error_message = "Echo frame not received"
    elif not result.rx_received:
        result.error_message = "Loopback RX frame not received"
    elif not result.echo_data_correct:
        result.error_message = "Echo frame data mismatch"
    elif not result.rx_data_correct:
        result.error_message = "Loopback RX frame data mismatch"
    else:
        result.passed = True

    return result


def test_classic_can_bitrate(dev: GsUsb, bitrate: int) -> TestResult:
    """Test a single Classic CAN bitrate."""
    test_name = f"Classic CAN {bitrate // 1000}k"

    # Configure bitrate
    if not dev.set_bitrate(bitrate):
        result = TestResult(test_name)
        result.error_message = f"Failed to set bitrate {bitrate}"
        return result

    # Start device with loopback
    flags = GS_CAN_MODE_NORMAL | GS_CAN_MODE_HW_TIMESTAMP | GS_CAN_MODE_LOOP_BACK
    dev.start(flags)

    # Run test
    result = run_single_test(
        dev, test_name, is_fd=False, expected_data=TEST_DATA_CLASSIC
    )

    # Stop device
    dev.stop()

    return result


def test_canfd_bitrate(dev: GsUsb, arb_bitrate: int, data_bitrate: int) -> TestResult:
    """Test a CAN FD bitrate combination."""
    test_name = f"CAN FD {arb_bitrate // 1000}k / {data_bitrate // 1000000}M"

    # Configure arbitration bitrate
    if not dev.set_bitrate(arb_bitrate):
        result = TestResult(test_name)
        result.error_message = f"Failed to set arbitration bitrate {arb_bitrate}"
        return result

    # Configure data bitrate
    if not dev.set_data_bitrate(data_bitrate):
        result = TestResult(test_name)
        result.error_message = f"Failed to set data bitrate {data_bitrate}"
        return result

    # Start device with loopback and FD mode
    flags = (
        GS_CAN_MODE_NORMAL
        | GS_CAN_MODE_HW_TIMESTAMP
        | GS_CAN_MODE_LOOP_BACK
        | GS_CAN_MODE_FD
    )
    dev.start(flags)

    # Run test
    result = run_single_test(dev, test_name, is_fd=True, expected_data=TEST_DATA_FD)

    # Stop device
    dev.stop()

    return result


def print_result(result: TestResult, verbose: bool = False):
    """Print test result."""
    status = "✓ PASS" if result.passed else "✗ FAIL"
    print(f"  {status}  {result.name}")
    if not result.passed and result.error_message:
        print(f"         Error: {result.error_message}")
    if verbose and not result.passed:
        print(
            f"         Echo received: {result.echo_received}, data OK: {result.echo_data_correct}"
        )
        print(
            f"         RX received: {result.rx_received}, data OK: {result.rx_data_correct}"
        )


def main():
    print("=" * 60)
    print("GS-USB Bitrate Test Suite")
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

    # Check device capabilities
    capability = dev.device_capability
    print(f"Device clock: {capability.fclk_can / 1_000_000:.1f} MHz")
    print(f"Feature flags: 0x{capability.feature:08x}")
    print(f"CAN FD support: {'Yes' if dev.supports_fd else 'No'}")
    print()

    results = []

    # Test Classic CAN bitrates
    print("-" * 60)
    print("Testing Classic CAN Bitrates")
    print("-" * 60)

    for bitrate in CLASSIC_CAN_BITRATES:
        result = test_classic_can_bitrate(dev, bitrate)
        results.append(result)
        print_result(result)

    # Test CAN FD bitrates (if supported)
    if dev.supports_fd:
        print()
        print("-" * 60)
        print("Testing CAN FD Bitrates")
        print("-" * 60)

        for arb_bitrate in FD_ARBITRATION_BITRATES:
            for data_bitrate in FD_DATA_BITRATES:
                result = test_canfd_bitrate(dev, arb_bitrate, data_bitrate)
                results.append(result)
                print_result(result)
    else:
        print()
        print("Skipping CAN FD tests (device does not support CAN FD)")

    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed > 0:
        print("Failed tests:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}: {r.error_message}")
        print()

    if failed == 0:
        print("All tests PASSED! ✓")
        return 0
    else:
        print(f"Some tests FAILED! ✗ ({failed}/{total})")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        raise
