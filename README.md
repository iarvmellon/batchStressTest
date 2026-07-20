# Batch Stress Test

This project sends SPDH sales over TCP and then closes the corresponding
batches with CLOSE BATCH requests.

## Files

- `main.py`: main entry point and runtime configuration.
- `send_packets.py`: payload construction, TCP transport, response parsing,
  sequence/transmission tracking, and sale sending.
- `close_remaining_batches.py`: reads pending sales from
  `sales_transmitted.json` and closes their batches sequentially.
- `sales_transmitted.json`: sales that have not been closed yet.
- `last_TRX.json`: persistent counter for the last transmitted transaction.

## Running

```bash
python main.py
```

`main.py` first calls `send_sales()` and then, after a one-second pause, calls
`close_batches()`.

To close batches already recorded in the JSON file:

```bash
python close_remaining_batches.py
```

## Configuration (`main.py`)

```python
HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TID = "00000006"
AMOUNT = "0001"
TRANSACTION_COUNT = 5
INCREMENT_BATCH_PER_SALE = True
```

`TIMEOUT` is the maximum TCP response wait in seconds. `AMOUNT` is the sale
amount in minor currency units. `INCREMENT_BATCH_PER_SALE=False` sends all
sales in one batch; `True` increments the batch for every sale.

`send_sales()` accepts a delay between sales. `close_batches()` also accepts a
delay, but it is applied only when `parallel=False`. The remaining-batches
script sends closes sequentially.

## Sequence and transmission numbers

A sequence has the form:

```text
001 | 531 | 4750
shift | batch field | suffix
```

TANGO displays the batch with a leading `1`, so `001531....` represents batch
`1531`. The sequence increases by 10 and the transmission number increases by
1. Transmission numbers use two digits (`00`–`99`) and roll over.

`last_TRX.json` is updated for every reservation and provides the next values,
even if the sales history file is deleted.

## Sales history

`sales_transmitted.json` is an array with one entry per sale:

```json
[
  {
    "sequence_number": "0015314750",
    "transmission_number": "04",
    "batch_number": "1531",
    "saved_at": "2026-07-20T13:09:31",
    "approved": true
  }
]
```

`approved` is `true` for response codes `000` and `001`, and `false` for a
failure or timeout. In a CLOSE BATCH, approved sales count as 1 and failed
sales count as 0. The total amount is the approved count multiplied by
`AMOUNT`.

After a successful CLOSE BATCH, all sales belonging to that batch are removed
from `sales_transmitted.json`. On failure they remain for retry.

## Notes

- `transmission_number` is two digits; `300` is not valid for this payload.
- Do not delete `last_TRX.json` if numbering must continue from the last values.

## Closing pending batches

The normal workflow is to run `main.py`. It sends the sales first and then
closes the pending batches. When closing a large number of batches (for
example, approximately 355 CLOSE BATCH requests), the SPDH endpoint may stop
returning data after roughly 100 requests and the socket response can be
empty. This is an endpoint/device limitation or overload condition, not an
indication that the Python process failed.

Use `close_remaining_batches.py`. Unlike a burst/parallel
close, this script sends the CLOSE BATCH requests sequentially and inserts a
delay between them. This avoids flooding SPDH and prevents the endpoint from
returning empty responses. If a request fails, its batch remains in
`sales_transmitted.json`; successful closes are removed automatically and can
therefore be retried safely.
