# GS-USB Protocol Explanation

GS-USB is a USB-to-CAN protocol used by the Linux kernel's `gs_usb.ko` driver to communicate with USB-CAN adapters. Here's a comprehensive breakdown:

## Protocol Overview

GS-USB uses **USB control transfers** for configuration and **bulk transfers** for CAN frame data. It's designed to be simple, efficient, and compatible with Linux SocketCAN.

## USB Endpoints

```
Control Endpoint 0:  Configuration commands (GET_STATE, SET_BITTIMING, etc.)
Bulk IN Endpoint:    CAN frames from device → host
Bulk OUT Endpoint:   CAN frames from host → device
```

## Control Requests (USB Control Transfers)

Commands sent via USB control messages to endpoint 0:

| Command | Value | Direction | Purpose |
|---------|-------|-----------|---------|
| `GS_USB_BREQ_HOST_FORMAT` | 0 | OUT | Set byte order (legacy) |
| `GS_USB_BREQ_BITTIMING` | 1 | OUT | Configure nominal bit timing |
| `GS_USB_BREQ_MODE` | 2 | OUT | Start/stop channel, set mode flags |
| `GS_USB_BREQ_BERR` | 3 | OUT | Enable/disable bus error reporting (deprecated) |
| `GS_USB_BREQ_BT_CONST` | 4 | IN | Get bit timing constraints |
| `GS_USB_BREQ_DEVICE_CONFIG` | 5 | IN | Get device info (channels, version) |
| `GS_USB_BREQ_TIMESTAMP` | 6 | IN | Get hardware timestamp |
| `GS_USB_BREQ_IDENTIFY` | 7 | OUT | Blink LED (locate device) |
| `GS_USB_BREQ_GET_USER_ID` | 8 | IN | Get user-defined ID |
| `GS_USB_BREQ_SET_USER_ID` | 9 | OUT | Set user-defined ID |
| `GS_USB_BREQ_DATA_BITTIMING` | 10 | OUT | Configure CAN FD data phase timing |
| `GS_USB_BREQ_BT_CONST_EXT` | 11 | IN | Get extended timing constraints (CAN FD) |
| `GS_USB_BREQ_SET_TERMINATION` | 12 | OUT | Enable/disable 120Ω termination |
| `GS_USB_BREQ_GET_TERMINATION` | 13 | IN | Get termination state |
| `GS_USB_BREQ_GET_STATE` | 14 | IN | Get CAN state (error-active/passive/bus-off) |

## Data Structures

### 1. Device Configuration (`GS_USB_BREQ_DEVICE_CONFIG`)

```c
struct gs_device_config {
    u8 reserved1;
    u8 reserved2;
    u8 reserved3;
    u8 icount;           // Number of CAN channels (0 = 1 channel)
    __le32 sw_version;   // Firmware version
    __le32 hw_version;   // Hardware version
} __packed;
```

### 2. Mode Configuration (`GS_USB_BREQ_MODE`)

```c
struct gs_device_mode {
    __le32 mode;   // GS_CAN_MODE_RESET or GS_CAN_MODE_START
    __le32 flags;  // Mode flags (see below)
} __packed;
```

**Mode Flags** (bitfield):
```c
#define GS_CAN_MODE_NORMAL                   0
#define GS_CAN_MODE_LISTEN_ONLY              BIT(0)   // Monitor mode
#define GS_CAN_MODE_LOOP_BACK                BIT(1)   // Loopback mode
#define GS_CAN_MODE_TRIPLE_SAMPLE            BIT(2)   // Sample bus 3x
#define GS_CAN_MODE_ONE_SHOT                 BIT(3)   // No auto-retransmit
#define GS_CAN_MODE_HW_TIMESTAMP             BIT(4)   // Enable timestamps
#define GS_CAN_MODE_PAD_PKTS_TO_MAX_PKT_SIZE BIT(7)   // Pad frames to max size
#define GS_CAN_MODE_FD                       BIT(8)   // CAN FD mode
#define GS_CAN_MODE_BERR_REPORTING           BIT(12)  // Report error frames
```

### 3. Bit Timing (`GS_USB_BREQ_BITTIMING`)

```c
struct gs_device_bittiming {
    __le32 prop_seg;    // Propagation segment
    __le32 phase_seg1;  // Phase segment 1
    __le32 phase_seg2;  // Phase segment 2
    __le32 sjw;         // Synchronization jump width
    __le32 brp;         // Bit rate prescaler
} __packed;
```

### 4. CAN State (`GS_USB_BREQ_GET_STATE`)

```c
struct gs_device_state {
    __le32 state;   // CAN state enum (see below)
    __le32 rxerr;   // RX error counter
    __le32 txerr;   // TX error counter
} __packed;

enum gs_can_state {
    GS_CAN_STATE_ERROR_ACTIVE = 0,   // Normal operation
    GS_CAN_STATE_ERROR_WARNING,      // TEC/REC > 96
    GS_CAN_STATE_ERROR_PASSIVE,      // TEC/REC > 127
    GS_CAN_STATE_BUS_OFF,            // TEC > 255
    GS_CAN_STATE_STOPPED,
    GS_CAN_STATE_SLEEPING
};
```

## Bulk Transfer Data Format

### CAN Frame Structure (`gs_host_frame`)

The frame structure is **variable length** depending on:
- Classic CAN vs CAN FD
- Hardware timestamp enabled/disabled
- Data length

```c
struct gs_host_frame {
    // Header (always present, 12 bytes)
    u32 echo_id;        // Echo ID for TX, 0xFFFFFFFF for RX
    __le32 can_id;      // CAN ID + flags
    u8 can_dlc;         // DLC (0-8 for Classic, 0-15 for CAN FD)
    u8 channel;         // CAN channel number
    u8 flags;           // Frame flags (see below)
    u8 reserved;
    
    // Data payload (variable)
    union {
        u8 classic_can_data[8];        // Classic CAN
        u8 classic_can_ts_data[8];     // Classic + timestamp
        u8 canfd_data[64];             // CAN FD
        u8 canfd_ts_data[64];          // CAN FD + timestamp
    };
    
    // Timestamp (optional, 4 bytes)
    __le32 timestamp_us;  // Only if HW_TIMESTAMP enabled
} __packed;
```

### Frame Flags

```c
#define GS_CAN_FLAG_OVERFLOW  BIT(0)  // RX overflow occurred
#define GS_CAN_FLAG_FD        BIT(1)  // CAN FD frame
#define GS_CAN_FLAG_BRS       BIT(2)  // Bit rate switch
#define GS_CAN_FLAG_ESI       BIT(3)  // Error state indicator
```

### CAN ID Field

The `can_id` field encodes the CAN identifier **plus** flag bits:

```c
// Standard vs Extended
#define CAN_EFF_FLAG  0x80000000  // Extended frame format
#define CAN_RTR_FLAG  0x40000000  // Remote transmission request
#define CAN_ERR_FLAG  0x20000000  // Error frame

// ID masks
#define CAN_SFF_MASK  0x000007FF  // Standard frame: 11-bit ID
#define CAN_EFF_MASK  0x1FFFFFFF  // Extended frame: 29-bit ID

// Examples
// Standard ID 0x123:        0x00000123
// Extended ID 0x12345:      0x80012345
// RTR frame with ID 0x456:  0x40000456
// Error frame (bus-off):    0x20000040
```

## Protocol Flow

### 1. Device Initialization (Driver Probe)

```
Host                              Device
  |                                  |
  |------ HOST_FORMAT (0) --------> | Set byte order
  |<-------- OK ------------------- |
  |                                  |
  |------ DEVICE_CONFIG (5) -------> | Get capabilities
  |<---- { icount, sw_ver } -------- |
  |                                  |
  |------ BT_CONST (4) ------------> | Get timing constraints
  |<---- { tseg1_min, tseg1_max } -- |
  |                                  |
  |------ BT_CONST_EXT (11) -------> | Get CAN FD constraints (if supported)
  |<---- { dtseg1_min, ... } ------- |
```

### 2. Channel Start Sequence

```
Host                              Device
  |                                  |
  |------ BITTIMING (1) -----------> | Set nominal bit timing
  |<-------- OK ------------------- |
  |                                  |
  |------ DATA_BITTIMING (10) -----> | Set CAN FD data phase (optional)
  |<-------- OK ------------------- |
  |                                  |
  |------ MODE (2) ----------------> | Start channel with flags
  |  { mode=START, flags=0x1014 }   | (FD + HW_TIMESTAMP + BERR_REPORTING)
  |<-------- OK ------------------- |
  |                                  |
  | Device powers on CAN transceiver|
  | and initializes controller      |
```

### 3. CAN Frame Transmission (Host → Device)

```
Host                              Device
  |                                  |
  |== Bulk OUT Transfer ===========>| CAN frame
  | gs_host_frame {                 |
  |   echo_id: 0,                   | Echo ID assigned by host
  |   can_id: 0x123,                |
  |   can_dlc: 8,                   |
  |   flags: 0,                     |
  |   data: [AA BB CC ...]          |
  | }                               |
  |                                  |
  |                Device transmits frame on CAN bus
  |                                  |
  |<== Bulk IN Transfer ============| Echo frame
  | gs_host_frame {                 |
  |   echo_id: 0,                   | Same echo_id
  |   can_id: 0x123,                |
  |   flags: 0,                     |
  |   timestamp_us: 12345           | Actual TX timestamp
  | }                               |
```

**Key Point**: The **echo frame** is critical for flow control. The host tracks up to 10 outstanding TX requests using `echo_id` (0-9). When an echo is received, that slot becomes available for a new transmission.

### 4. CAN Frame Reception (Device → Host)

```
Device                            Host
  |                                  |
  | CAN frame received on bus       |
  |                                  |
  |== Bulk IN Transfer ==============>
  | gs_host_frame {                 |
  |   echo_id: 0xFFFFFFFF,          | Special value for RX
  |   can_id: 0x456,                |
  |   can_dlc: 8,                   |
  |   flags: GS_CAN_FLAG_FD,        |
  |   data: [11 22 33 ...],         |
  |   timestamp_us: 56789           |
  | }                               |
```

### 5. Error Frame Reporting

When `BERR_REPORTING` is enabled, error state changes are reported as special CAN error frames:

```
Device                            Host
  |                                  |
  | Error counter exceeds threshold |
  | (e.g., TEC > 127)               |
  |                                  |
  |== Bulk IN Transfer ==============>
  | gs_host_frame {                 |
  |   echo_id: 0xFFFFFFFF,          | RX frame
  |   can_id: 0x20000204,           | CAN_ERR_FLAG | CAN_ERR_CRTL | CAN_ERR_CNT
  |   can_dlc: 8,                   |
  |   data: [                       |
  |     0,                          | data[0]: arbitration lost
  |     0x20,                       | data[1]: CAN_ERR_CRTL_TX_PASSIVE
  |     0,                          | data[2]: protocol error type
  |     0, 0, 0,                    | data[3-5]: reserved
  |     128,                        | data[6]: TX error counter
  |     0                           | data[7]: RX error counter
  |   ]                             |
  | }                               |
```

The **Linux kernel** parses these error frames and updates the interface state, which is visible via `ip link show`.

## Flow Control & Buffering

### TX Flow Control

The driver limits outstanding TX requests to **10 URBs** (`GS_MAX_TX_URBS`):

1. Host allocates `echo_id` from pool (0-9)
2. Sends frame via bulk OUT with that `echo_id`
3. Device transmits frame on CAN bus
4. Device sends echo frame back via bulk IN with same `echo_id`
5. Host releases that `echo_id` slot

If all 10 slots are in use, `netif_stop_queue()` blocks further transmissions until an echo is received.

### RX Flow Control

The driver pre-allocates **30 RX URBs** (`GS_MAX_RX_URBS`) that continuously poll the bulk IN endpoint:

```
Host submits 30 URBs → Device fills them as frames arrive → Callback resubmits URB
```

The firmware must handle burst traffic by buffering frames in its own RX queue (the CF3 has 317-frame capacity).

## Hardware Timestamp Mechanism

When `GS_CAN_MODE_HW_TIMESTAMP` is enabled:

1. Device maintains a **32-bit 1 MHz timer** (wraps every ~71 minutes)
2. Each frame includes a `timestamp_us` field (microseconds)
3. Host periodically queries device time via `GS_USB_BREQ_TIMESTAMP` (every 30 minutes)
4. Host maintains a **time counter** that tracks timer overflow
5. Timestamps are converted to kernel's `ktime_t` for `skb_hwtstamps`

This allows sub-millisecond timestamp accuracy for received frames.

## Error Handling

### Overflow Reporting

If the device's RX FIFO overflows:

```c
gs_host_frame {
    flags: GS_CAN_FLAG_OVERFLOW,
    // ... frame data ...
}
```

The driver converts this to a Linux `CAN_ERR_CRTL_RX_OVERFLOW` error frame.

### Bus-Off Recovery

When device enters bus-off (TEC > 255):

1. Device sends error frame with `CAN_ERR_FLAG | CAN_ERR_BUSOFF`
2. Linux driver updates state to `CAN_STATE_BUS_OFF`
3. Device automatically recovers (monitors 128×11 recessive bits)
4. Device sends error frame with `CAN_ERR_RESTARTED`
5. Linux driver updates state back to `CAN_STATE_ERROR_ACTIVE`

## Feature Negotiation

The device advertises features via `gs_device_bt_const.feature` bitmask:

```c
#define GS_CAN_FEATURE_LISTEN_ONLY              BIT(0)
#define GS_CAN_FEATURE_LOOP_BACK                BIT(1)
#define GS_CAN_FEATURE_TRIPLE_SAMPLE            BIT(2)
#define GS_CAN_FEATURE_ONE_SHOT                 BIT(3)
#define GS_CAN_FEATURE_HW_TIMESTAMP             BIT(4)
#define GS_CAN_FEATURE_IDENTIFY                 BIT(5)
#define GS_CAN_FEATURE_USER_ID                  BIT(6)
#define GS_CAN_FEATURE_PAD_PKTS_TO_MAX_PKT_SIZE BIT(7)
#define GS_CAN_FEATURE_FD                       BIT(8)
#define GS_CAN_FEATURE_REQ_USB_QUIRK_LPC546XX   BIT(9)
#define GS_CAN_FEATURE_BT_CONST_EXT             BIT(10)
#define GS_CAN_FEATURE_TERMINATION              BIT(11)
#define GS_CAN_FEATURE_BERR_REPORTING           BIT(12)
#define GS_CAN_FEATURE_GET_STATE                BIT(13)
```

The driver checks these features before enabling corresponding `ctrlmode` flags in the CAN subsystem.

## Summary

**GS-USB Protocol Characteristics**:

✅ **Simple**: USB control for config, bulk for data  
✅ **Efficient**: Bulk transfers for high-throughput frame exchange  
✅ **Extensible**: Feature flags allow backward-compatible enhancements  
✅ **SocketCAN Native**: Maps directly to Linux CAN subsystem primitives  
✅ **Error Transparent**: Reports all CAN error states via error frames  
✅ **Timestamp Support**: Hardware timestamping for precise timing
