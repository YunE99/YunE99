from enum import Enum


# 데이터 타입 Enum
class eDataType(Enum):
    SBYTE = "SByte"
    BYTE = "Byte"
    SHORT = "Short"
    USHORT = "uShort"
    INT = "Int"
    UINT = "uInt"
    LONG = "Long"
    ULONG = "uLong"
    FLOAT = "Float"
    DOUBLE = "Double"
    BOOL = "Bool"
    CHAR = "Char"
    STRING = "String"


# 서버 타입 Enum
class eServerType(Enum):
    DEV = "Dev"
    QA = "Qa"
    LIVE = "Live"


# 서버 정보 클래스
class ServerInfo:
    SERVER_TYPE = eServerType.DEV
    MY_IP_DEV_QA = "175.201.23.229"
    MY_IP_DEV_LIVE = "175.201.23.229"
    
    PORT_SERVER_IN = 20022
    PORT_SERVER_OUT_DEV = 24522
    PORT_SERVER_OUT_QA = 24501
    PORT_SERVER_OUT_LIVE = 24502

    MAX_BUFFER_SIZE = 65535
    TARGET_BUFFER_SIZE = MAX_BUFFER_SIZE


# 패킷 정보 클래스
class PacketInfo:
    class Max:
        SBYTE = 127
        BYTE = 255
        SHORT = 32767
        USHORT = 65535
        INT = 2147483647  # 21억
        UINT = 4294967295  # 42억
        LONG = 9223372036854775807  # 100경
        ULONG = 18446744073709551615  # 1000경
        FLOAT = 3.402823e38
        DOUBLE = 1.79769313486232e307

    class Bit:
        BYTE = 8
        SHORT = 16
        INT = 32
        LONG = 64
        FLOAT = 32
        DOUBLE = 64
        BOOL = 8
        CHAR = 16

    class Byte:
        BYTE = 1
        SHORT = 2
        INT = 4
        LONG = 8
        FLOAT = 4
        DOUBLE = 8
        BOOL = 1
        CHAR = 2

    @staticmethod
    def get_size(value):
        """ 데이터 타입별 크기 반환 """
        if isinstance(value, int):
            if value >= 0:
                if value <= PacketInfo.Max.BYTE:
                    return PacketInfo.Byte.BYTE
                elif value <= PacketInfo.Max.SHORT:
                    return PacketInfo.Byte.SHORT
                elif value <= PacketInfo.Max.INT:
                    return PacketInfo.Byte.INT
                else:
                    return PacketInfo.Byte.LONG
            else:
                if value >= -PacketInfo.Max.SHORT:
                    return PacketInfo.Byte.SHORT
                elif value >= -PacketInfo.Max.INT:
                    return PacketInfo.Byte.INT
                else:
                    return PacketInfo.Byte.LONG
        elif isinstance(value, float):
            return PacketInfo.Byte.FLOAT
        elif isinstance(value, bool):
            return PacketInfo.Byte.BOOL
        elif isinstance(value, str):
            return len(value) * PacketInfo.Byte.CHAR
        return 0

    @staticmethod
    def get_max(value):
        """ 데이터 타입별 최대값 반환 """
        if isinstance(value, int):
            if value >= 0:
                if value <= PacketInfo.Max.BYTE:
                    return PacketInfo.Max.BYTE
                elif value <= PacketInfo.Max.SHORT:
                    return PacketInfo.Max.SHORT
                elif value <= PacketInfo.Max.INT:
                    return PacketInfo.Max.INT
                else:
                    return PacketInfo.Max.LONG
            else:
                if value >= -PacketInfo.Max.SHORT:
                    return PacketInfo.Max.SHORT
                elif value >= -PacketInfo.Max.INT:
                    return PacketInfo.Max.INT
                else:
                    return PacketInfo.Max.LONG
        elif isinstance(value, float):
            return PacketInfo.Max.FLOAT
        return 0

    @staticmethod
    def get_bit(value):
        """ 데이터 타입별 비트 크기 반환 """
        if isinstance(value, int):
            if value >= 0:
                if value <= PacketInfo.Max.BYTE:
                    return PacketInfo.Bit.BYTE
                elif value <= PacketInfo.Max.SHORT:
                    return PacketInfo.Bit.SHORT
                elif value <= PacketInfo.Max.INT:
                    return PacketInfo.Bit.INT
                else:
                    return PacketInfo.Bit.LONG
            else:
                if value >= -PacketInfo.Max.SHORT:
                    return PacketInfo.Bit.SHORT
                elif value >= -PacketInfo.Max.INT:
                    return PacketInfo.Bit.INT
                else:
                    return PacketInfo.Bit.LONG
        elif isinstance(value, float):
            return PacketInfo.Bit.FLOAT
        elif isinstance(value, bool):
            return PacketInfo.Bit.BOOL
        elif isinstance(value, str):
            return len(value) * PacketInfo.Bit.CHAR
        return 0

    @staticmethod
    def get_byte(value):
        """ 데이터 타입별 바이트 크기 반환 """
        return PacketInfo.get_size(value)
