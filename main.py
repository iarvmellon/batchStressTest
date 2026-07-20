"""Configurable sales and batch-closing runner."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from send_packets import STATE_FILE, reserve_message_numbers, send_close_batch, send_packets
INITIAL_SEQUENCE_NUMBER = "0015304720"
INITIAL_TRANSMISSION_NUMBER = "70"

HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TID = "00000006"
AMOUNT = "0001"
TRANSACTION_COUNT = 355
INCREMENT_BATCH_PER_SALE = True
STATE = Path(STATE_FILE)


def send_sales(host, port, timeout, count, tid, amount, delay=0.0,
               increment_batch_per_sale=False):
    """Send sales serially, waiting *delay* seconds between requests."""
    return send_packets(host, port, timeout, state_file=STATE, nof_trx=count,
                        tid=tid, amount=amount, delay_seconds=delay,
                        send_close_batches=False,
                        increment_batch_per_sale=increment_batch_per_sale,
                        initial_sequence_number=INITIAL_SEQUENCE_NUMBER,
                        initial_transmission_number=INITIAL_TRANSMISSION_NUMBER)


def close_batches(host, port, timeout, tid, amount, delay=0.0,
                  parallel=True, batch_numbers=None):
    """Close batches sequentially or concurrently.

    ``delay`` is used only between sequential requests. In parallel mode all
    requests are submitted together, so no inter-request delay is applied.
    """
    selected = set(batch_numbers or [])
    try:
        state_data = json.loads(STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"State file is empty or invalid: {STATE}") from exc
    history = state_data if isinstance(state_data, list) else state_data.get("history", [])
    sales = [(entry["sequence_number"], entry.get("approved", False))
             for entry in history]
    grouped = {}
    for sale_sequence, approved in sales:
        batch = sale_sequence[3:6]
        if selected and batch not in selected:
            continue
        sequence, count = grouped.get(batch, (sale_sequence, 0))
        grouped[batch] = (sequence, count + int(approved))

    requests = []
    for sale_sequence, approved_count in grouped.values():
        sequence, transmission = reserve_message_numbers(
            STATE, INITIAL_SEQUENCE_NUMBER, INITIAL_TRANSMISSION_NUMBER,
            record=False)
        # Keep the sale's batch field while advancing the close sequence by 10.
        sequence = f"{sequence[:3]}{sale_sequence[3:6]}{sequence[6:]}"
        requests.append((transmission, sequence, approved_count))

    def send(request):
        return request[1], send_close_batch(host, port, timeout, request[0], request[1],
                         request[2], tid, amount)

    if parallel and len(requests) > 1:
        with ThreadPoolExecutor(max_workers=len(requests)) as pool:
            results = list(pool.map(send, requests))
    else:
        results = []
        for index, request in enumerate(requests):
            if index:
                time.sleep(delay)
            results.append(send(request))

    successful_batches = {sequence[3:6] for sequence, ok in results if ok}
    if successful_batches:
        state_data = json.loads(STATE.read_text(encoding="utf-8"))
        history = state_data if isinstance(state_data, list) else state_data.get("history", [])
        remaining = [
            e for e in history
            if e.get("sequence_number", "")[3:6] not in successful_batches
        ]
        STATE.write_text(json.dumps(remaining, indent=2) + "\n", encoding="utf-8")


def main():
    send_sales(HOST, PORT, TIMEOUT, TRANSACTION_COUNT, TID, AMOUNT,
                       delay=0.1,
                       increment_batch_per_sale=INCREMENT_BATCH_PER_SALE)

    # Allow the final sale response to settle before closing the batch.
    time.sleep(1.0)
    
    close_batches(HOST, PORT, TIMEOUT, TID, AMOUNT, delay=1.0,
                  parallel=True)


if __name__ == "__main__":
    main()
