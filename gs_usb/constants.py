# gs_usb mode flags
GS_CAN_MODE_NORMAL = 0
GS_CAN_MODE_LISTEN_ONLY = 1 << 0
GS_CAN_MODE_LOOP_BACK = 1 << 1
GS_CAN_MODE_TRIPLE_SAMPLE = 1 << 2
GS_CAN_MODE_ONE_SHOT = 1 << 3
GS_CAN_MODE_HW_TIMESTAMP = 1 << 4
GS_CAN_MODE_IDENTIFY = 1 << 5
GS_CAN_MODE_USER_ID = 1 << 6
GS_CAN_MODE_PAD_PKTS_TO_MAX_PKT_SIZE = 1 << 7
GS_CAN_MODE_FD = 1 << 8
GS_CAN_MODE_BERR_REPORTING = 1 << 12

# gs_usb device feature flags (from BT_CONST response)
GS_CAN_FEATURE_LISTEN_ONLY = 1 << 0
GS_CAN_FEATURE_LOOP_BACK = 1 << 1
GS_CAN_FEATURE_TRIPLE_SAMPLE = 1 << 2
GS_CAN_FEATURE_ONE_SHOT = 1 << 3
GS_CAN_FEATURE_HW_TIMESTAMP = 1 << 4
GS_CAN_FEATURE_IDENTIFY = 1 << 5
GS_CAN_FEATURE_USER_ID = 1 << 6
GS_CAN_FEATURE_PAD_PKTS_TO_MAX_PKT_SIZE = 1 << 7
GS_CAN_FEATURE_FD = 1 << 8
GS_CAN_FEATURE_REQ_USB_QUIRK_LPC546XX = 1 << 9
GS_CAN_FEATURE_BT_CONST_EXT = 1 << 10
GS_CAN_FEATURE_TERMINATION = 1 << 11
GS_CAN_FEATURE_BERR_REPORTING = 1 << 12
GS_CAN_FEATURE_GET_STATE = 1 << 13

# Special address description flags for the CAN_ID
CAN_EFF_FLAG = 0x80000000  # EFF/SFF is set in the MSB
CAN_RTR_FLAG = 0x40000000  # remote transmission request
CAN_ERR_FLAG = 0x20000000  # error message frame

# Valid bits in CAN ID for frame formats
CAN_SFF_MASK = 0x000007FF  # standard frame format (SFF)
CAN_EFF_MASK = 0x1FFFFFFF  # extended frame format (EFF)
CAN_ERR_MASK = 0x1FFFFFFF  # omit EFF, RTR, ERR flags

CAN_SFF_ID_BITS = 11
CAN_EFF_ID_BITS = 29

# CAN payload length and DLC definitions according to ISO 11898-1
CAN_MAX_DLC = 8
CAN_MAX_DLEN = 8

# CAN FD payload length and DLC definitions
CANFD_MAX_DLC = 15
CANFD_MAX_DLEN = 64

# CAN FD frame flags (in gs_host_frame.flags field)
GS_CAN_FLAG_OVERFLOW = 1 << 0  # RX overflow occurred
GS_CAN_FLAG_FD = 1 << 1  # CAN FD frame
GS_CAN_FLAG_BRS = 1 << 2  # Bit rate switch (FD frame transmitted at data bitrate)
GS_CAN_FLAG_ESI = 1 << 3  # Error state indicator

# DLC to length conversion for CAN FD
CANFD_DLC_TO_LEN = [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64]

# CAN ID length
CAN_IDLEN = 4
