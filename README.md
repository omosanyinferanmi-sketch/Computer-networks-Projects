# DHCP Client Simulation

Project structure for the DHCP client simulation. The assignment brief is kept in `Project Scope/`.

Suggested layout:

```text
.
|-- Project Scope/       # Assignment brief
|-- docs/                # Design notes and protocol flow
|-- pyproject.toml       # Project metadata and package configuration
|-- src/
|   `-- dhcp_client/      # Python package
|-- tests/               # unittest suite
`-- README.md
```

## Set up and test

From the project root, install the package in editable mode and run the initial
tests with Python's standard-library `unittest`. Activate the project's
virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

The package import test establishes the baseline before networking code is
added.

Suggested modules:

- `src/dhcp_client/client.py`: client workflow and DHCP state transitions
- `src/dhcp_client/packet.py`: DHCP message construction and parsing
- `tests/test_client.py` and `tests/test_packet.py`: client and packet tests
