# DHCP Client Simulation: Implementation Plan

## Goal

Build a Python DHCP client that crafts DHCP messages, broadcasts Discover and Request packets over UDP, parses Offer and Acknowledge responses, and reports the resulting lease without applying it to the host operating system.

## Planning Note

The confirmed requirements are the DHCP DORA process, UDP broadcasting, creating raw sockets, crafting and broadcasting Discover, parsing an Offer (for example, from a home router), sending Request, and processing the final Acknowledge to obtain a lease. Confirm any additional rubric details and platform constraints against `DHCP Client Simulation.pdf` before implementation.

**Socket note:** DHCP messages are DHCP/BOOTP payloads carried over UDP, normally from client port 68 to server port 67. A UDP socket with broadcast enabled is the normal portable approach. `SOCK_RAW` has platform- and privilege-specific behavior; clarify what the course means by “raw socket” and demonstrate it separately if required, rather than assuming a raw IP socket is needed for DHCP.

## Steps

### 1. Lock down the rubric and test environment

- Confirm the required Python version, supported operating system, output/demo format, and how the rubric expects the raw-socket learning objective to be demonstrated alongside UDP-based DHCP.
- Use a local isolated lab or an authorized network for live broadcasts. Do not run experiments on a shared network without permission.
- Keep the client in report-only mode: it must not alter the host's IP configuration, routes, or DNS settings.
- Record the rubric as acceptance criteria before implementation.

**Exit check:** The socket API, authorized test environment, and expected lease output are clear.

### 2. Establish the Python project foundation

- Keep implementation code under `src/dhcp_client/` and tests under `tests/`.
- Add minimal project metadata and test configuration for the confirmed Python version.
- Define module responsibilities before coding:
  - `client.py`: client workflow and state transitions.
  - `packet.py`: DHCP/BOOTP header and option encoding/decoding.
  - `transport.py`: UDP broadcast send/receive, timeouts, and interface selection.
  - `__main__.py`: safe command-line entry point and report-only lease output.
- Prefer Python's standard library unless the rubric requires another dependency.

**Exit check:** The package imports and the chosen test command runs, even before feature code is added.

### 3. Define DHCP data and protocol constants

- Define the BOOTP/DHCP fixed header, magic cookie, transaction ID, client hardware address, broadcast flag, and DHCP message-type option.
- Define typed representations for Offer details and the final lease, including the offered address and relevant options such as server identifier, lease duration, subnet mask, router, and DNS where provided.
- Keep packet encoding/parsing independent of networking and client state transitions.

**Exit check:** Data structures and constants can be unit-tested without sending network traffic.

### 4. Implement DHCP packet handling

- Craft a DHCP Discover payload with a valid BOOTP header, transaction ID, client hardware address, magic cookie, and required options.
- Parse Offer payloads and extract the offered IP address (`yiaddr`) and server identifier; retain relevant lease options.
- Craft a DHCP Request that identifies the requested IP and selected DHCP server.
- Parse the final ACK and verify its message type, transaction ID, client identity, and lease fields before reporting success.
- Reject malformed, mismatched, or unexpected packets explicitly; test valid messages, missing options, malformed input, and encoding/decoding round trips.

**Exit check:** Packet tests pass and verify important protocol fields and error cases.

### 5. Implement the client state machine

- Implement the required Discover → Offer → Request → Acknowledge sequence as explicit client states.
- Match responses to the active transaction and only request an address from a valid Offer.
- Handle no Offer, invalid Offer, NAK, and timeout without reporting a lease as acquired.
- Treat a valid ACK as the point at which the client reports the lease; do not configure the operating system interface.

**Exit check:** State-machine tests cover the successful exchange and each required failure path.

### 6. Connect the simulation transport

- Use a UDP socket with `SO_BROADCAST`, sending DHCP client traffic from UDP port 68 to server port 67 and listening for server responses on port 68 as appropriate to the operating system.
- Make broadcast address, interface, timeout, and socket mode explicit; avoid silently selecting an unintended interface.
- Include a documented raw-socket exercise/path to satisfy the learning objective, isolated behind the transport boundary and tested only in an authorized lab. Document platform and privilege requirements. Use UDP broadcast for the DHCP exchange unless the rubric specifically requires the DHCP datagram to be sent through a raw IP or link-layer socket.
- Keep an injectable/fake transport for deterministic unit tests; do not change host IP configuration, routes, or DNS settings.

**Exit check:** Unit tests need no live network; live DORA tests are opt-in and limited to an authorized environment.

### 7. Add the user-facing run flow

- Provide a clear opt-in command for live broadcast and require or display the selected interface and broadcast mode before sending.
- Display Discover, Offer, Request, and ACK progress plus the lease details actually received.
- Clearly distinguish a reported DHCP lease from an address configured on the host; do not configure the host automatically.
- Report invalid input, NAK, malformed responses, and timeout clearly.

**Exit check:** A fresh user can run the required demonstration using the documented steps.

### 8. Verify behavior and edge cases

- Run packet/state-machine tests with a fake transport, including mismatched transaction IDs, wrong message types, malformed options, timeouts, and NAK.
- In an authorized isolated environment, verify that Discover is broadcast, the Offer is parsed, Request selects the offered address/server, and a matching ACK produces a reported lease.
- Confirm source/destination UDP ports, broadcast settings, interface selection, and any platform-specific raw-socket behavior required by the rubric.
- Verify that the program does not modify host network settings and does not claim success before a valid ACK.
- Check every acceptance criterion from Step 1 and fix failures in the owning layer.

**Exit check:** All required behaviors have a passing test or a documented manual demonstration.

### 9. Document and prepare submission

- Document setup, live-test prerequisites, required privileges, supported platforms, selected interface, and test commands in the root `README.md`.
- Describe the DORA flow and the distinction between UDP payload crafting and raw sockets in `docs/` if useful or required.
- Include known limitations and make clear that the program reports a lease but does not apply network configuration.
- Confirm the final demonstration and submission contents against the assignment rubric.

**Exit check:** Another student can install or run the project and reproduce the demonstrated behavior from the documentation.

## Working Rhythm

We will implement one step at a time. Before each step, we will identify its expected behavior; after implementation, we will run the narrowest relevant tests before moving on. If the assignment brief conflicts with this roadmap, the brief takes priority.
