# Batch Stress Test

This project sends SPDH SALE requests over TCP and can close pending batches
with CLOSE BATCH requests.

## Files

- `main.py`: runtime configuration and main SALE runner.
- `send_packets.py`: payload construction, TCP transport, response parsing,
  counter management, and SALE/CLOSE sending.
- `close_remaining_batches.py`: closes pending sales sequentially.
- `next_TRX_per_TID.json`: the next SALE values for every configured TID.
- `sales_transmitted.json`: SALE requests that have not been closed yet.

## Configuration

The main settings are defined in `main.py`:

```python
HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TIDS = ["00003971", "00003981", "..."]
AMOUNT = "0001"
TRANSACTION_COUNT = 2
INCREMENT_BATCH_PER_SALE = True
```

- `TIMEOUT` is the maximum response wait in seconds.
- `AMOUNT` is expressed in minor currency units.
- `TRANSACTION_COUNT` is the number of SALE requests sent for each TID.
- `INCREMENT_BATCH_PER_SALE=True` advances the batch and `rcncltPrdId` after
  every SALE. When it is `False`, only `rcncltPrdId` advances.

## Running SALE requests

```bash
python main.py
```

SALE requests are sent sequentially. The program sends `TRANSACTION_COUNT`
requests for each entry in `TIDS`, with a short delay between requests and
between TIDs.

The CLOSE BATCH worker block in `main.py` is currently commented out. Use the
dedicated script described below to close entries in `sales_transmitted.json`.

## Next transaction per TID

`next_TRX_per_TID.json` contains one entry for every configured TID:

```json
{
  "tids": {
    "00003971": {
      "sequence_number": "0015470200",
      "transmission_number": "00"
    },
    "00003981": {
      "sequence_number": "0015470200",
      "transmission_number": "00"
    }
  }
}
```

The configured `sequence_number` is the exact value sent by the next SALE for
that TID. The `transmission_number` sent by every SALE and CLOSE request is
always `00`.

After a SALE is executed, its TID entry is advanced and written atomically back
to `next_TRX_per_TID.json`. For example, with
`INCREMENT_BATCH_PER_SALE=True`:

```text
send:  0015470200
store: 0015480210

send:  0015480210
store: 0015490220
```

If TANGO rejects the transmission/sequence with response code `899` or an
equivalent invalid-sequence message, the rejected SALE is removed from
`sales_transmitted.json` and the next values are not advanced.

## Sequence format

```text
001 | 547 | 020 | 0
shift | batch field | rcncltPrdId | final digit
```

For `0015470200`:

- Shift: `001`
- Batch number displayed by TANGO: `1547`
- `rcncltPrdId`: `020`
- Final digit: `0`

The batch's leading `1` is not stored separately. `batch_number` is therefore
not present in either JSON file.

Adding 10 advances `rcncltPrdId` and keeps the final digit unchanged. With
per-SALE batch increments enabled, the three-digit batch field also advances
by one.

## Pending SALE history

`sales_transmitted.json` is an array with one entry per pending SALE:

```json
[
  {
    "sequence_number": "0015470200",
    "transmission_number": "00",
    "saved_at": "2026-07-23T15:30:00",
    "tid": "00003971",
    "approved": true
  }
]
```

`approved` is `true` for response codes `000` and `001`, and `false` for a
failure or timeout. An approved SALE contributes a count of 1 to CLOSE BATCH;
an unapproved SALE contributes 0. The total amount is the approved count
multiplied by `AMOUNT`.

Each pending SALE is identified by the combination of `tid` and
`sequence_number`. A SALE is removed from `sales_transmitted.json` only when
its own CLOSE BATCH receives the successful response code `000`. Exactly one
matching entry is removed.

If CLOSE BATCH returns any other response code (including `001`), times out,
or encounters a socket error, the SALE remains in `sales_transmitted.json` so
it can be retried. This also prevents a successful CLOSE for one TID from
deleting a failed pending SALE belonging to another TID with the same sequence
number.

## Closing pending batches

```bash
python close_remaining_batches.py
```

The script reads `sales_transmitted.json` and closes pending batches
sequentially, with a delay between requests. Each request uses the TID stored
in its SALE entry. Legacy entries without a TID use `DEFAULT_TID`.

Sequential closing is recommended for large pending histories because the SPDH
endpoint can stop returning data when it receives a large burst of CLOSE BATCH
requests.
