# DHCP Client Simulation

A Python DHCP client project that constructs and parses DHCP packets, runs the
Discover → Offer → Request → ACK exchange, and reports a lease without applying
network settings to the host computer.

## Current implementation

- DHCP Discover and Request packet builders use Scapy and include the BOOTP
  transaction ID, client MAC, broadcast flag, UDP ports, and DHCP options.
- Offer and ACK parsers validate the response layers, message type, transaction
  ID, client MAC, offered address, server identifier, and lease time where
  required. A matching DHCP NAK is detected explicitly.
- The client has INIT, SELECTING, REQUESTING, BOUND, and FAILED states and
  reports a lease only after a matching ACK.
- The exchange uses an injectable transport interface. A fake transport
  supports offline DORA tests; the current live adapter uses Scapy's
  `srp1`.
- The client does not configure the host's address, routes, or DNS settings.

The current packet and state-machine implementation has 20 passing unit tests
covering Discover/Request construction, valid Offer/ACK responses, invalid and
mismatched responses, DORA success, timeout, and NAK behavior. These tests do
not send DHCP traffic.

## Project layout

```text
Project Scope/             Assignment brief and implementation plan
src/dhcp_client/
  client.py                Client state machine and current Scapy adapter
  packet.py                DHCP packet construction and reply validation
tests/
  test_client.py           Fake-transport state-machine tests
  test_packet.py           Offline packet construction and parsing tests
pyproject.toml             Package metadata and Scapy dependency
```

## Set up and run offline tests

From the project root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Live networking status and safety

The DORA state machine is implemented and tested offline. The live adapter is
not yet a finalized, documented DHCP transport: interface selection,
explicit UDP broadcast socket behavior, and the course's raw-socket requirement
still need to be confirmed and implemented. Do not treat the current Scapy
adapter as a portable live-demo solution.

The current `client.py` main guard starts the live exchange when the module is
run directly. Until the opt-in command-line flow is implemented, do not run it
on a shared or unauthorized network. DHCP broadcasts should only be tested in
an isolated lab or on a network for which you have explicit authorization.
The program is intended to report a lease only; it must never apply network
configuration to the host.

## Remaining work by person

| Owner | Remaining work | Completion evidence |
|---|---|---|
| If you are Emmanuel | Confirm the assignment's exact requirements for “raw socket,” supported OS, and demo environment. Implement the live transport behind the existing `DhcpTransport.exchange(packet, timeout)` contract, with explicit interface selection, broadcast destination, UDP ports 68/67, broadcast socket settings, response listening, and timeout handling. Add transport-focused tests that do not require live traffic, then validate the live exchange in an authorized isolated environment. | Rubric requirements recorded; transport tests pass; authorized demo verifies Discover → Offer → Request → ACK and the selected interface/ports. |
| If you Asiwaju | Add a safe, clearly opt-in CLI that shows the selected interface and DORA progress and reports errors without changing host networking. Extend lease reporting/parsing for optional subnet mask, router, and DNS details when provided. Add client tests for invalid Offer and ACK/Offer mismatch, update this README with final setup/run/platform instructions and limitations, and prepare the submission/demo checklist. Coordinate the CLI with Emmanuel's transport options. | CLI does not broadcast by default; offline tests pass; README supports a fresh setup and authorized demo; final checklist matches the course rubric. |

Emmanuel's transport interface/options should be agreed with Asiwaju before
the CLI integration. Both owners should check the final behavior against
`Project Scope/DHCP Client Simulation.pdf`; the course rubric takes precedence
over this project checklist.
