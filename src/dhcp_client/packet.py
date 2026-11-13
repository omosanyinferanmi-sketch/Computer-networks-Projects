from dataclasses import dataclass
from ipaddress import AddressValueError, IPv4Address
from scapy.all import BOOTP, DHCP, Ether, IP, UDP, Packet

_INVALID_MAC_MESSAGE = "client_mac must be a valid six-byte MAC address"


def _bootp_packet(client_mac: str, xid: int) -> Packet:
    parts = client_mac.split(":")
    if len(parts) != 6 or any(len(part) != 2 for part in parts):
        raise ValueError(_INVALID_MAC_MESSAGE)

    try:
        mac_bytes = bytes.fromhex("".join(parts))
    except ValueError as ex:
        raise ValueError(_INVALID_MAC_MESSAGE) from ex

    if not 0 <= xid <= 0xFFFFFFFF:
        raise ValueError("xid must be a 32-bit unsigned integer")

    normalized_mac = ":".join(f"{part:02x}" for part in mac_bytes)

    return (
        Ether(src=normalized_mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src="0.0.0.0", dst="255.255.255.255")
        / UDP(sport=68, dport=67)
        / BOOTP(
            op=1,
            htype=1,
            hlen=6,
            xid=xid,
            flags=0x8000,  # Ask the server to broadcast its reply.
            chaddr=mac_bytes,
        )
    )


class PacketValidationErr(ValueError):
    "This is raised when a DHCP response is invalid for this client exchange"


@dataclass(frozen=True)
class DhcpLeaseInfo:
    address: str
    server_id: str
    lease_time: int | None


def _mac_bytes(client_mac: str) -> bytes:
    parts = client_mac.split(":")
    if len(parts) != 6 or any(len(part) != 2 for part in parts):
        raise PacketValidationErr(_INVALID_MAC_MESSAGE)

    try:
        return bytes.fromhex("".join(parts))
    except ValueError as ex:
        raise PacketValidationErr(_INVALID_MAC_MESSAGE) from ex


def _get_option(options: list, name: str, *, required: bool = True):
    values = [
        option[1]
        for option in options
        if isinstance(option, tuple) and len(option) == 2 and option[0] == name
    ]

    if len(values) > 1:
        raise PacketValidationErr(f"DHCP response contains duplicate {name!r} options")
    if not values:
        if required:
            raise PacketValidationErr(f"DHCP response is missing {name!r}")
        return None

    return values[0]


def _validate_reply_identity(
    packet: Packet,
    *,
    expected_xid: int,
    expected_mac: str,
) -> tuple[Packet, list]:
    if not packet.haslayer(BOOTP) or not packet.haslayer(DHCP):
        raise PacketValidationErr("Response must contain BOOTP and DHCP layers")

    bootp = packet[BOOTP]
    if bootp.op != 2:
        raise PacketValidationErr("BOOTP response is not a server reply")
    if bootp.htype != 1 or bootp.hlen != 6:
        raise PacketValidationErr("Response does not identify an Ethernet client")
    if bootp.xid != expected_xid:
        raise PacketValidationErr("Response transaction ID does not match")
    if bytes(bootp.chaddr)[:6] != _mac_bytes(expected_mac):
        raise PacketValidationErr("Response client MAC does not match")

    return bootp, packet[DHCP].options


def _ipv4(value: object, field_name: str) -> str:
    try:
        address = IPv4Address(value)
    except (AddressValueError, TypeError) as ex:
        raise PacketValidationErr(f"DHCP response has an invalid {field_name}") from ex

    if address.is_unspecified or address.is_multicast or address == IPv4Address("255.255.255.255"):
        raise PacketValidationErr(f"DHCP response has an unusable {field_name}")

    return str(address)


def _parse_reply(
    packet: Packet,
    *,
    expected_xid: int,
    expected_mac: str,
    expected_message_type: int,
    require_lease_time: bool,
) -> DhcpLeaseInfo:
    bootp, options = _validate_reply_identity(
        packet,
        expected_xid=expected_xid,
        expected_mac=expected_mac,
    )
    message_type = _get_option(options, "message-type")
    if type(message_type) is not int or message_type != expected_message_type:
        raise PacketValidationErr("Unexpected DHCP message type")

    address = _ipv4(bootp.yiaddr, "yiaddr")
    server_id = _ipv4(_get_option(options, "server_id"), "server identifier")

    lease_time = _get_option(
        options,
        "lease_time",
        required=require_lease_time,
    )
    if lease_time is not None and (type(lease_time) is not int or lease_time <= 0):
        raise PacketValidationErr("DHCP lease time must be a positive integer")

    return DhcpLeaseInfo(
        address=address,
        server_id=server_id,
        lease_time=lease_time,
    )


def parse_offer(packet: Packet, *, expected_xid: int, expected_mac: str) -> DhcpLeaseInfo:
    return _parse_reply(
        packet,
        expected_xid=expected_xid,
        expected_mac=expected_mac,
        expected_message_type=2,  # DHCPOFFER
        require_lease_time=False,
    )


def parse_ack(packet: Packet, *, expected_xid: int, expected_mac: str) -> DhcpLeaseInfo:
    return _parse_reply(
        packet,
        expected_xid=expected_xid,
        expected_mac=expected_mac,
        expected_message_type=5,  # DHCPACK
        require_lease_time=True,
    )


def is_nak(packet: Packet, *, expected_xid: int, expected_mac: str) -> bool:
    _, options = _validate_reply_identity(
        packet,
        expected_xid=expected_xid,
        expected_mac=expected_mac,
    )
    message_type = _get_option(options, "message-type")
    if type(message_type) is not int:
        raise PacketValidationErr("DHCP message type must be an integer")
    return message_type == 6


def create_discover_packet(client_mac: str, xid: int) -> Packet:
    return _bootp_packet(client_mac, xid) / DHCP(
        options=[
            ("message-type", "discover"),
            ("param_req_list", [1, 3, 6]),  # Subnet mask, router, and DNS.
            "end",
        ]
    )


def create_request_packet(
    client_mac: str,
    xid: int,
    requested_ip: str,
    server_id: str,
) -> Packet:
    return _bootp_packet(client_mac, xid) / DHCP(
        options=[
            ("message-type", "request"),
            ("requested_addr", requested_ip),
            ("server_id", server_id),
            "end",
        ]
    )