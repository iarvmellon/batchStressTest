"""Close a contiguous range of batches."""
import json
import time
from datetime import datetime

from send_packets import STATE_FILE
import socket
from main import close_batches

HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TID = "00000006"
AMOUNT = "0000"
# TRANSACTIONS_PER_BATCH = 1
DELAY_SECONDS = 1.0
# Sequence corresponding to the first batch (1374): shift 001, batch 374.
SEQUENCE_NUMBER = "0013741350"
TRANSMISSION_NUMBER = "36"


def close_batch(batch_number: int, offset: int) -> None:
    # The SPDH sequence carries a three-digit batch field; use the protocol
    # representation of the supplied number (1374 -> 374, 1509 -> 509).
    batch_field = f"{batch_number % 1000:03d}"
    suffix = int(SEQUENCE_NUMBER[6:]) + offset * 10
    if suffix >= 10000:
        raise ValueError("Sequence suffix exhausted for requested range")
    sequence = f"{SEQUENCE_NUMBER[:3]}{batch_field}{suffix:04d}"
    transmission = f"{(int(TRANSMISSION_NUMBER) + offset) % 100:02d}"
    payload = build_close_batch_payload(
        transmission, sequence, TID, AMOUNT, TRANSACTIONS_PER_BATCH
    )
    print(
        f"Sending CLOSE BATCH batch={batch_number} sequence={sequence} "
        f"transmission={transmission} bytes={len(payload)}",
        flush=True,
    )
    with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as sock:
        sock.sendall(payload)
        print(f"CLOSE BATCH batch={batch_number}: sent", flush=True)
        sock.settimeout(TIMEOUT)
        response = sock.recv(4096)
    print(f"CLOSE BATCH batch={batch_number}: received {len(response)} bytes", flush=True)
    print(f"Batch {batch_number}: {response_summary(response)}", flush=True)


def main() -> None:
    print(f"Sales start time: {datetime.now().isoformat(timespec='seconds')}", flush=True)
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    history = state if isinstance(state, list) else state.get("history", [])
    sales = [
        (entry["sequence_number"], entry.get("approved", False))
        for entry in history
    ]
    if not sales:
        raise RuntimeError("No matching sales found in .packet_state.json")

    print (sales)
    close_batches(HOST, PORT, TIMEOUT, TID, AMOUNT,
                  delay=DELAY_SECONDS, parallel=False)


if __name__ == "__main__":
    main()
