import secrets
from enum import Enum, auto
from typing import Protocol

from scapy.all import Packet, conf, srp1

from .packet import (
    DhcpLeaseInfo,
    PacketValidationErr,
    create_discover_packet,
    create_request_packet,
    is_nak,
    parse_ack,
    parse_offer,
)


def random_mac() -> str:
    mac = bytearray(secrets.token_bytes(6))
    mac[0] = (mac[0] & 0xFE) | 0x02
    return ":".join(f"{part:02x}" for part in mac)


class DhcpTransport(Protocol):
    def exchange(self, packet: Packet, timeout: float) -> Packet | None:
        """Send one DHCP message and wait for its response."""


class ScapyTransport:
    def exchange(self, packet: Packet, timeout: float) -> Packet | None:
        previous_check_ipaddr = conf.checkIPaddr
        try:
            conf.checkIPaddr = False
            return srp1(packet, timeout=timeout, verbose=0)
        finally:
            conf.checkIPaddr = previous_check_ipaddr


class DhcpState(Enum):
    INIT = auto()
    SELECTING = auto()
    REQUESTING = auto()
    BOUND = auto()
    FAILED = auto()


class DhcpNakError(RuntimeError):
    """Raised when the DHCP server rejects the requested address."""


class DhcpClient:
    def __init__(
        self,
        transport: DhcpTransport,
        client_mac: str,
        xid: int,
        timeout: float = 5,
    ) -> None:
        self.transport = transport
        self.client_mac = client_mac
        self.xid = xid
        self.timeout = timeout
        self.state = DhcpState.INIT

    def acquire_lease(self) -> DhcpLeaseInfo:
        if self.state is not DhcpState.INIT:
            raise RuntimeError("DHCP exchange can only be started once")

        try:
            self.state = DhcpState.SELECTING
            discover = create_discover_packet(self.client_mac, self.xid)
            offer_packet = self.transport.exchange(discover, self.timeout)
            if offer_packet is None:
                raise TimeoutError("Timed out waiting for DHCP Offer")

            offer = parse_offer(
                offer_packet,
                expected_xid=self.xid,
                expected_mac=self.client_mac,
            )

            self.state = DhcpState.REQUESTING
            request = create_request_packet(
                self.client_mac,
                self.xid,
                requested_ip=offer.address,
                server_id=offer.server_id,
            )
            ack_packet = self.transport.exchange(request, self.timeout)
            if ack_packet is None:
                raise TimeoutError("Timed out waiting for DHCP ACK")

            if is_nak(
                ack_packet,
                expected_xid=self.xid,
                expected_mac=self.client_mac,
            ):
                raise DhcpNakError("DHCP server sent a NAK")

            lease = parse_ack(
                ack_packet,
                expected_xid=self.xid,
                expected_mac=self.client_mac,
            )
            if (lease.address, lease.server_id) != (offer.address, offer.server_id):
                raise PacketValidationErr("ACK does not match the selected Offer")

            self.state = DhcpState.BOUND
            return lease
        finally:
            if self.state is not DhcpState.BOUND:
                self.state = DhcpState.FAILED


def send_discover(packet: Packet, timeout: float = 5) -> Packet | None:
    return ScapyTransport().exchange(packet, timeout)


def main() -> None:
    client_mac = random_mac()
    xid = secrets.randbits(32)
    client = DhcpClient(ScapyTransport(), client_mac, xid)

    print(f"Starting simulator with MAC address: {client_mac}")
    try:
        lease = client.acquire_lease()
    except (TimeoutError, DhcpNakError, PacketValidationErr) as ex:
        print(f"DHCP exchange failed: {ex}")
        raise SystemExit(1) from ex

    print("DHCP lease received (not applied to this computer):")
    print(f"  Address: {lease.address}")
    print(f"  Server: {lease.server_id}")
    print(f"  Lease time: {lease.lease_time}")


if __name__ == "__main__":
    main()
