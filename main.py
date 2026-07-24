"""Configurable sales and batch-closing runner."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import socket
import time

from send_packets import (
    STATE_FILE,
    remove_pending_sale,
    reserve_message_numbers,
    send_close_batch,
    send_packets,
)
INITIAL_SEQUENCE_NUMBER = "0015304720"
INITIAL_TRANSMISSION_NUMBER = "70"

HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TIDS = ["00000006",\
       "00003981",\
       "00003451",\
       "00003461",\
       "00003471",\
       "00003491",\
       "00003511",\
       "00003611",\
       "00003612",\
       "00003621",\
       "00003622",\
       "00003631",\
       "00003632",\
       "00004111",\
       "00003691",\
       "00003701",\
       "00003711",\
       "00003741",\
       "00003751",\
       "00004062",\
       "00004071",\
       "00003371",\
       "00003372",\
       "00003381",\
       "00003391",\
       "00003392",\
       "00003402",\
       "00003431",\
       "00003441"]
AMOUNT = "0001"
TRANSACTION_COUNT = 30
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
    sales = [
        (entry["sequence_number"], entry.get("approved", False))
        for entry in history
        if entry.get("tid") == tid
    ]
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
            record=False, tid=tid)
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
            if not (
                e.get("tid") == tid
                and e.get("sequence_number", "")[3:6] in successful_batches
            )
        ]
        STATE.write_text(json.dumps(remaining, indent=2) + "\n", encoding="utf-8")


def main():
    print(
        f"Sending {TRANSACTION_COUNT} sales sequentially for each of "
        f"{len(TIDS)} TIDs ({len(TIDS) * TRANSACTION_COUNT} total)",
        flush=True,
    )
    sales_by_tid = {}
    for tid in TIDS:
        sales_by_tid[tid] = send_sales(
            HOST,
            PORT,
            TIMEOUT,
            TRANSACTION_COUNT,
            tid,
            AMOUNT,
            delay=0.1,
            increment_batch_per_sale=INCREMENT_BATCH_PER_SALE,
        )
        # time.sleep(1)

    time.sleep(1.0)

    def remove_closed_sale(sale_sequence, tid):
        remove_pending_sale(STATE, sale_sequence, tid)

    def close_tid(tid, sales):
        closed = 0
        for sale_sequence, approved in sales:
            close_sequence, transmission = reserve_message_numbers(
                STATE,
                INITIAL_SEQUENCE_NUMBER,
                INITIAL_TRANSMISSION_NUMBER,
                record=False,
                tid=tid,
            )
            close_sequence = (
                f"{close_sequence[:3]}{sale_sequence[3:6]}{close_sequence[6:]}"
            )
            sale_count = int(approved)
            try:
                success = send_close_batch(
                    HOST,
                    PORT,
                    TIMEOUT,
                    transmission,
                    close_sequence,
                    sale_count,
                    tid,
                    AMOUNT,
                )
                if success:
                    remove_closed_sale(sale_sequence, tid)
                    closed += 1
            except socket.timeout:
                print(f"TID={tid} batch=1{sale_sequence[3:6]}: timeout", flush=True)
            except OSError as exc:
                print(
                    f"TID={tid} batch=1{sale_sequence[3:6]}: socket error: {exc}",
                    flush=True,
                )
        return closed

    print(f"Starting {len(TIDS)} CLOSE BATCH threads", flush=True)
    with ThreadPoolExecutor(max_workers=len(TIDS)) as executor:
        futures = {
            executor.submit(close_tid, tid, sales): tid
            for tid, sales in sales_by_tid.items()
        }
        for future in as_completed(futures):
            tid = futures[future]
            try:
                closed = future.result()
                print(
                    f"TID={tid} CLOSE completed: "
                    f"closed={closed}, remaining={TRANSACTION_COUNT - closed}",
                    flush=True,
                )
            except Exception as exc:
                print(f"TID={tid} CLOSE worker failed: {exc}", flush=True)


if __name__ == "__main__":
    main()
