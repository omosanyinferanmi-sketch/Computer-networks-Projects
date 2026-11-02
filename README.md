# DHCP Client Simulation

Project structure for the DHCP client simulation. The assignment brief is kept in `Project Scope/`.

Suggested layout:

```text
.
|-- Project Scope/       # Assignment brief
|-- docs/                # Design notes and protocol flow
|-- src/
|   `-- dhcp_client/      # Python package
|-- tests/               # Python tests
`-- README.md
```

Suggested modules:

- `src/dhcp_client/client.py`: client workflow and DHCP state transitions
- `src/dhcp_client/packet.py`: DHCP message construction and parsing
- `tests/test_client.py` and `tests/test_packet.py`: client and packet tests
