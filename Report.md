# Batch Closing Stress Test Report

## Test objective

The test evaluated the behavior of the payment terminal when a large number
of sales and CLOSE BATCH requests are sent in a short period of time.

## Sales phase

- **Total sales:** 355
- **Batch assignment:** one different batch number per sale
- **Expected result:** 355 distinct batches were created and all were ready to
  be closed independently.

## Batch-closing phase

After the sales completed, all CLOSE BATCH requests were dispatched together,
without a delay between requests. This produced a burst of traffic and caused
an SPDH flooding condition at the TANGO endpoint.

## Observed behavior

The first approximately 100–150 CLOSE BATCH requests were processed normally.
After that point, TANGO stopped returning a response for subsequent requests.
Those requests therefore timed out or returned an empty response, and the
corresponding CLOSE BATCH operations were not completed.

## Progressive observations

The following page references document the progression of the run:

- [Pages 1–4 — no CLOSE BATCH completed](#pages-14--no-close-batch-completed)
- [Pages 5–7 — CLOSE BATCH activity begins](#pages-57--close-batch-activity-begins)
- [Page 8 — first visible failure](#page-8--first-visible-failure)
- [Pages 9 onward — empty responses and failed closes](#pages-9-onward--empty-responses-and-failed-closes)

### Pages 1–4 — no CLOSE BATCH completed

The initial pages contain the sales activity, but no CLOSE BATCH operation was
completed during this part of the run.

### Pages 5–7 — CLOSE BATCH activity begins

CLOSE BATCH requests start appearing as the system begins processing the batch
closing phase.

![Page 5 — CLOSE BATCH activity begins](images/Page_5.PNG)

*Page 5 — CLOSE BATCH requests begin to appear.*

![Page 6 — CLOSE BATCH processing continues](images/Page_6.PNG)

*Page 6 — CLOSE BATCH processing continues.*

### Page 8 — first visible failure

The first clear failure appears on Page 8. From this point, the endpoint begins
showing signs of overload and responses become unreliable.

![Page 8 — first visible failure](images/Page_8.PNG)

*Page 8 — the first visible failure during the batch-closing phase.*

### Pages 9 onward — empty responses and failed closes

Subsequent pages show missing or empty SPDH responses. The associated CLOSE
BATCH requests do not complete successfully.

![Page 9 — empty responses and failed closes](images/Page_9.PNG)

*Page 9 — empty SPDH responses and unsuccessful CLOSE BATCH operations.*

## Conclusion

Sending hundreds of CLOSE BATCH requests concurrently is not reliable for this
endpoint. The observed failure is consistent with request flooding or device
overload rather than a payload-generation problem.

## Recommended execution mode

CLOSE BATCH requests should be sent sequentially with a delay between them.
This avoids flooding the endpoint and allows each response to be received before
the next request is transmitted. Failed batches should remain pending so they
can be retried after the endpoint has recovered.
