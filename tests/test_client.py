import importlib
import unittest
from unittest.mock import patch

from scapy.all import BOOTP, DHCP, Ether, IP, Packet, UDP

import dhcp_client.client as client_module
from dhcp_client.packet import create_discover_packet


CLIENT_MAC = "02:00:00:00:00:01"
XID = 1234


def make_reply(message_type: str | int) -> Packet:
    options = [
        ("message-type", message_type),
        ("server_id", "192.0.2.1"),
        "end",
    ]
    if message_type in ("offer", "ack"):
        options.insert(2, ("lease_time", 3600))

    packet = (
        Ether()
        / IP()
        / UDP()
        / BOOTP(
            op=2,
            htype=1,
            hlen=6,
            xid=XID,
            yiaddr="192.0.2.10" if message_type != 6 else "0.0.0.0",
            chaddr=bytes.fromhex(CLIENT_MAC.replace(":", "")),
        )
        / DHCP(options=options)
    )
    return Ether(bytes(packet))


class FakeTransport:
    def __init__(self, *responses: Packet | None) -> None:
        self.responses = list(responses)
        self.sent_packets: list[Packet] = []
        self.timeouts: list[float] = []

    def exchange(self, packet: Packet, timeout: float) -> Packet | None:
        self.sent_packets.append(packet)
        self.timeouts.append(timeout)
        return self.responses.pop(0)


class ClientTests(unittest.TestCase):
    def test_import_does_not_send_packet(self):
        try:
            with patch("scapy.all.srp1") as send:
                importlib.reload(client_module)
                send.assert_not_called()
        finally:
            importlib.reload(client_module)

    def test_send_discover_sends_only_when_explicitly_called(self):
        packet = create_discover_packet(CLIENT_MAC, XID)
        with patch("dhcp_client.client.srp1", return_value=None) as send:
            response = client_module.send_discover(packet, timeout=2)

        self.assertIsNone(response)
        send.assert_called_once_with(packet, timeout=2, verbose=0)

    def test_dora_success_uses_offer_in_request_and_returns_lease(self):
        transport = FakeTransport(make_reply("offer"), make_reply("ack"))
        client = client_module.DhcpClient(transport, CLIENT_MAC, XID, timeout=2)

        lease = client.acquire_lease()

        self.assertEqual(lease.address, "192.0.2.10")
        self.assertEqual(lease.server_id, "192.0.2.1")
        self.assertEqual(lease.lease_time, 3600)
        self.assertEqual(client.state, client_module.DhcpState.BOUND)
        self.assertEqual(len(transport.sent_packets), 2)

        request = Ether(bytes(transport.sent_packets[1]))
        self.assertEqual(request[UDP].sport, 68)
        self.assertEqual(request[UDP].dport, 67)
        request_options = dict(
            option for option in request[DHCP].options if isinstance(option, tuple)
        )
        self.assertEqual(request_options["message-type"], 3)
        self.assertEqual(request_options["requested_addr"], "192.0.2.10")
        self.assertEqual(request_options["server_id"], "192.0.2.1")
        self.assertEqual(transport.timeouts, [2, 2])

    def test_offer_timeout_fails_without_sending_request(self):
        transport = FakeTransport(None)
        client = client_module.DhcpClient(transport, CLIENT_MAC, XID)

        with self.assertRaisesRegex(TimeoutError, "Offer"):
            client.acquire_lease()

        self.assertEqual(client.state, client_module.DhcpState.FAILED)
        self.assertEqual(len(transport.sent_packets), 1)

    def test_ack_timeout_fails_after_request(self):
        transport = FakeTransport(make_reply("offer"), None)
        client = client_module.DhcpClient(transport, CLIENT_MAC, XID)

        with self.assertRaisesRegex(TimeoutError, "ACK"):
            client.acquire_lease()

        self.assertEqual(client.state, client_module.DhcpState.FAILED)
        self.assertEqual(len(transport.sent_packets), 2)

    def test_nak_fails_exchange(self):
        transport = FakeTransport(make_reply("offer"), make_reply(6))
        client = client_module.DhcpClient(transport, CLIENT_MAC, XID)

        with self.assertRaises(client_module.DhcpNakError):
            client.acquire_lease()

        self.assertEqual(client.state, client_module.DhcpState.FAILED)
        self.assertEqual(len(transport.sent_packets), 2)


if __name__ == "__main__":
    unittest.main()
