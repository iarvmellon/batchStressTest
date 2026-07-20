# Batch Stress Test

Το project στέλνει SPDH sales μέσω TCP και στη συνέχεια κλείνει τα batches
με CLOSE BATCH requests.

## Αρχεία

- `main.py`: κύριο entry point και όλες οι παράμετροι εκτέλεσης.
- `send_packets.py`: κατασκευή payloads, TCP αποστολή, parsing απαντήσεων και
  διαχείριση sequence/transmission numbers.
- `close_batch_range.py`: διαβάζει τις εκκρεμείς sales από το
  `sales_transmitted.json` και κλείνει σειριακά όλα τα batches.
- `sales_transmitted.json`: ιστορικό των sales που δεν έχουν κλείσει ακόμη.
- `last_TRX.json`: μόνιμος μετρητής της τελευταίας sale, ώστε η αρίθμηση να
  συνεχίζεται ακόμη κι αν διαγραφεί το ιστορικό.

## Εκτέλεση

```bash
python main.py
```

Το `main.py` καλεί πρώτα τη `send_sales()` και, μετά από καθυστέρηση ενός
δευτερολέπτου, τη `close_batches()`.

Για κλείσιμο των sales που υπάρχουν ήδη στο JSON:

```bash
python close_batch_range.py
```

## Κύριες παράμετροι (`main.py`)

```python
HOST = "10.1.110.84"
PORT = 28420
TIMEOUT = 5.0
TID = "00000006"
AMOUNT = "0001"
TRANSACTION_COUNT = 5
INCREMENT_BATCH_PER_SALE = True
```

- `TIMEOUT`: μέγιστος χρόνος αναμονής TCP απάντησης, σε δευτερόλεπτα.
- `AMOUNT`: ποσό κάθε sale σε minor currency units.
- `TRANSACTION_COUNT`: αριθμός sales.
- `INCREMENT_BATCH_PER_SALE=False`: όλες οι sales χρησιμοποιούν το ίδιο
  batch.
- `INCREMENT_BATCH_PER_SALE=True`: κάθε sale παίρνει batch αυξημένο κατά 1.

Η `send_sales()` δέχεται `delay` μεταξύ διαδοχικών sales. Η
`close_batches()` δέχεται επίσης `delay`, αλλά αυτό εφαρμόζεται μόνο όταν
`parallel=False`. Στο `close_batch_range.py` τα closes εκτελούνται σειριακά.

## Sequence και transmission

Ένα sequence έχει τη μορφή:

```text
001 | 531 | 4750
shift | batch field | suffix
```

Το TANGO εμφανίζει το batch με αρχικό `1`, άρα το `001531....` αντιστοιχεί
στο batch `1531`. Το sequence αυξάνεται κατά 10 και το transmission number
κατά 1 (δύο ψηφία, `00` έως `99`, με rollover).

Το `last_TRX.json` ενημερώνεται σε κάθε reservation και είναι η πηγή για την
επόμενη αρίθμηση.

## `sales_transmitted.json`

Το αρχείο περιέχει array εγγραφών, μία ανά sale:

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

Η `approved` είναι `true` για response code `000` ή `001` και `false` για
αποτυχία/timeout. Στο CLOSE BATCH κάθε επιτυχημένη sale μετράει ως 1 και
κάθε αποτυχημένη ως 0. Το συνολικό ποσό είναι το πλήθος των επιτυχημένων
sales επί `AMOUNT`.

Με επιτυχημένο CLOSE BATCH διαγράφονται από το JSON όλες οι sales του
συγκεκριμένου batch. Σε αποτυχία παραμένουν για επανάληψη.

## Σημειώσεις

- Το `transmission_number` είναι δύο ψηφία· τιμή όπως `300` δεν είναι έγκυρη
  για το συγκεκριμένο SPDH payload.
- Τα CLOSE BATCH requests του `close_batch_range.py` στέλνονται ένα-ένα με
  `DELAY_SECONDS` μεταξύ τους.
- Μην διαγράφετε το `last_TRX.json` αν θέλετε να συνεχιστεί η αρίθμηση από τις
  τελευταίες τιμές.
