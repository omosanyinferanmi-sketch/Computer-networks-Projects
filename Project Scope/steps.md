# DHCP Client Project Steps

This guide takes the Python DHCP client from environment setup through implementation and verification.

## 1. Check requirements and environment

- Confirm the required Python version, Windows version, expected demo, and what the assignment means by “raw socket.”
- Identify an authorized network or isolated lab for live broadcasts. Do not test on a shared network without permission.

## 2. Set up Python in VS Code

- Check Python with `py --version`.
- Create a virtual environment from the project root with `py -m venv .venv`.
- Activate it in PowerShell with `\.venv\Scripts\Activate.ps1`.
- Select `.venv` as the VS Code Python interpreter.
- Start with Python's standard library; use `unittest` unless the rubric requires another test framework.

## 3. Establish the package and test baseline

- Keep implementation in `src/dhcp_client/` and tests in `tests/`.
- Add project metadata and a documented test command.
- Verify the package imports and the initial tests run before adding networking.

## 4. Define DHCP message structures

- Specify the BOOTP/DHCP header, magic cookie, transaction ID, client hardware address, broadcast flag, message type, and options.
- Define how Offer details and lease information will be represented.

## 5. Build and test packet handling

- Implement DHCP Discover construction, Offer parsing, Request construction, and ACK/NAK parsing.
- Test valid packets, malformed or truncated options, unexpected message types, and mismatched transaction IDs offline.

## 6. Implement the DORA state machine

- Model Discover → Offer → Request → ACK explicitly.
- Request only an acceptable Offer, and report a lease only after receiving a matching ACK.
- Test success, NAK, invalid response, and timeout using a fake transport.

## 7. Add the socket transport

- DHCP normally carries a crafted DHCP payload over UDP, with client port 68 and server port 67; broadcast sending requires `SO_BROADCAST`.
- Make interface selection, timeout, and socket mode explicit.
- If the rubric literally requires `SOCK_RAW`, isolate that path and verify Windows privilege and platform constraints before relying on it.

## 8. Add a safe live-run command

- Make broadcasting opt-in and display the selected interface before sending.
- Show DORA progress and received lease details.
- Keep the tool report-only: it must not change the computer's IP, routes, or DNS settings.

## 9. Verify and document

- Run offline tests first, then test the full exchange in an authorized isolated environment.
- Verify broadcast behavior, ports, interface, Offer/ACK matching, timeout/NAK handling, and report-only behavior.
- Document setup, Windows permissions, run/test commands, limitations, and demo steps in `README.md` or `docs/`.
