from scapy.all import * # This imports all scapy modules, including DHCP and IP modules
import random 



conf.checkIPaddr = False  # Disable IP address checking to allow for DHCP packet crafting


# This function generates a random MAC address for the client.
def random_mac():
    mac = []
    for _ in range(6):
        mac.append(random.randint(0, 255))
    return ':'.join('%02x' % x for x in mac)


client_mac_addi = random_mac()
print(f" -> Starting simulator with MAC address: {client_mac_addi}")

# This func would craft a Discover packet
bootp_request = BOOTP(
op=1,  # BOOTREQUEST
    htype=1,  # Ethernet
    hlen=6,  # MAC address length
    xid=random.randint(1, 900000000),  # Random transaction ID
    chaddr=bytes.fromhex(client_mac_addi.replace(':', ''))  # Client MAC address
)


dhcp_request = DHCP(
    ("message-type", "discover"),
    ("parameter-req-list", ["router", "subnet_mask", "domain_server"]),
    ("end")
)

discover_packet = Ether(dst="ff:ff:ff:ff:ff:ff") / bootp_request / dhcp_request/ UDP(sport=68, dport=67) / IP(src="0.0.0.0", dst="255.255.255.255")

print(f"[*] Sending DHCP Discover packet...")
print( f" -> Sending DHCP Discover packet: {discover_packet.summary()}")

response = srp1(discover_packet, timeout=5, verbose=0)  # Send the packet and wait for a response

if response:
    print(f"response received from DHCP server: {response.summary()}")
    response.show()  # Display the details of the response packet
else:
    print("No response received from DHCP server.")
