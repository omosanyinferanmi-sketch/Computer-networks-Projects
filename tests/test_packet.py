import unittest
from scapy.all import BOOTP, DHCP, Ether, IP, UDP

from dhcp_client.packet import (
    create_discover_packet,
    create_request_packet,
    PacketValidationErr,
    is_nak,
    parse_ack,
    parse_offer,
)

CLIENT_MAC = "02:00:00:00:00:01"
XID = 1234

def make_reply(
    message_type: str | int,
    *,
    xid: int = XID,
    client_mac: str = CLIENT_MAC,
    yiaddr: str = "192.0.2.10",
    options: list | None = None,
):
    if options is None:
        options = [
            ("message-type", message_type),
            ("server_id", "192.0.2.1"),
            ("lease_time", 3600),
            "end",
        ]

    packet = (
        Ether()
        / IP()
        / UDP()
        / BOOTP(
            op=2,
            htype=1,
            hlen=6,
            xid=xid,
            yiaddr=yiaddr,
            chaddr=bytes.fromhex(client_mac.replace(":", "")),
        )
        / DHCP(options=options)
    )
    return Ether(bytes(packet))


class ReplyParsingTests(unittest.TestCase):
    def test_parse_valid_offer(self):
        offer = parse_offer(
            make_reply("offer"),
            expected_xid=XID,
            expected_mac=CLIENT_MAC,
        )
        self.assertEqual(offer.address, "192.0.2.10")
        self.assertEqual(offer.server_id, "192.0.2.1")
        self.assertEqual(offer.lease_time, 3600)

    def test_parse_valid_ack(self):
        lease = parse_ack(
            make_reply("ack"),
            expected_xid=XID,
            expected_mac=CLIENT_MAC,
        )
        self.assertEqual(lease.address, "192.0.2.10")
        self.assertEqual(lease.lease_time, 3600)

    def test_reject_mismatched_transaction_id(self):
        packet = make_reply("offer", xid=XID + 1)
        with self.assertRaisesRegex(PacketValidationErr, "transaction ID"):
            parse_offer(
                packet,
                expected_xid=XID,
                expected_mac=CLIENT_MAC,
            )

    def test_reject_missing_server_identifier(self):
        malformed = make_reply(
            "offer",
            options=[("message-type", "offer"), "end"],
        )
        with self.assertRaisesRegex(PacketValidationErr, "server_id"):
            parse_offer(
                malformed,
                expected_xid=XID,
                expected_mac=CLIENT_MAC,
            )

    def test_reject_wrong_message_type(self):
        packet = make_reply("offer")
        with self.assertRaisesRegex(PacketValidationErr, "message type"):
            parse_ack(
                packet,
                expected_xid=XID,
                expected_mac=CLIENT_MAC,
            )

    def test_reject_response_without_dhcp_layer(self):
        malformed = Ether() / IP() / UDP() / BOOTP(
            op=2,
            htype=1,
            hlen=6,
            xid=XID,
            yiaddr="192.0.2.10",
            chaddr=bytes.fromhex("020000000001"),
        )
        with self.assertRaisesRegex(PacketValidationErr, "BOOTP and DHCP"):
            parse_offer(
                malformed,
                expected_xid=XID,
                expected_mac=CLIENT_MAC,
            )

    def test_reject_response_for_different_client(self):
        packet = make_reply("offer", client_mac="02:00:00:00:00:02")
        with self.assertRaisesRegex(PacketValidationErr, "MAC"):
            parse_offer(
                packet,
                expected_xid=XID,
                expected_mac=CLIENT_MAC,
            )

    def test_reject_ack_without_lease_time(self):
        packet = make_reply(
            "ack",
            options=[
                ("message-type", "ack"),
                ("server_id", "192.0.2.1"),
                "end",
            ],
        )
        with self.assertRaisesRegex(PacketValidationErr, "lease_time"):
            parse_ack(
                packet,
                expected_xid=XID,
                expected_mac=CLIENT_MAC,
            )

    def test_is_nak_requires_matching_reply_and_identifies_nak(self):
        nak = make_reply(
            6,
            yiaddr="0.0.0.0",
            options=[
                ("message-type", 6),
                ("server_id", "192.0.2.1"),
                "end",
            ],
        )
        self.assertTrue(is_nak(nak, expected_xid=XID, expected_mac=CLIENT_MAC))

        with self.assertRaisesRegex(PacketValidationErr, "transaction ID"):
            is_nak(nak, expected_xid=XID + 1, expected_mac=CLIENT_MAC)


class PacketTests(unittest.TestCase):
    def decode(self, packet):
        return Ether(bytes(packet))

    def test_discover_packet_has_expected_layers_and_options(self):
        packet = self.decode(
            create_discover_packet("02:00:00:00:00:01", 1234)
        )

        self.assertTrue(packet.haslayer(Ether))
        self.assertTrue(packet.haslayer(IP))
        self.assertTrue(packet.haslayer(UDP))
        self.assertTrue(packet.haslayer(BOOTP))
        self.assertTrue(packet.haslayer(DHCP))
        self.assertEqual(packet[UDP].sport, 68)
        self.assertEqual(packet[UDP].dport, 67)
        self.assertEqual(packet[BOOTP].xid, 1234)
        self.assertEqual(packet[BOOTP].flags, 0x8000)
        self.assertEqual(packet[BOOTP].chaddr[:6], bytes.fromhex("020000000001"))

        options = dict(
            option for option in packet[DHCP].options
            if isinstance(option, tuple)
        )
        self.assertEqual(options["message-type"], 1)
        self.assertEqual(options["param_req_list"], [1, 3, 6])

    def test_request_packet_includes_selected_offer(self):
        packet = self.decode(
            create_request_packet(
                "02:00:00:00:00:01",
                1234,
                requested_ip="192.0.2.10",
                server_id="192.0.2.1",
            )
        )

        options = dict(
            option for option in packet[DHCP].options
            if isinstance(option, tuple)
        )
        self.assertEqual(options["message-type"], 3)
        self.assertEqual(options["requested_addr"], "192.0.2.10")
        self.assertEqual(options["server_id"], "192.0.2.1")

    def test_invalid_mac_is_rejected(self):
        for mac in ("not-a-mac", "02:00:00:00:00:1", "02:00:00:00:00:gg"):
            with self.subTest(mac=mac), self.assertRaises(ValueError):
                create_discover_packet(mac, 1234)

    def test_out_of_range_transaction_id_is_rejected(self):
        for xid in (-1, 0x1_0000_0000):
            with self.subTest(xid=xid), self.assertRaises(ValueError):
                create_discover_packet("02:00:00:00:00:01", xid)


if __name__ == "__main__":
    unittest.main()
