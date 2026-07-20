"""Close every batch represented in sales_transmitted.json."""
import json
from datetime import datetime

from send_packets import STATE_FILE
from main import close_batches

HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TID = "00000006"
AMOUNT = "0001"
DELAY_SECONDS = 1.0
# Sequence corresponding to the first batch (1374): shift 001, batch 374.
SEQUENCE_NUMBER = "0013741350"
TRANSMISSION_NUMBER = "36"


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

    close_batches(HOST, PORT, TIMEOUT, TID, AMOUNT,
                  delay=DELAY_SECONDS, parallel=False)


if __name__ == "__main__":
    main()
