# Operations

## Scan-event partition retention

`scan_event` is partitioned monthly by `event_time`. The retention setting is
two years. A scheduled maintenance operation should detach partitions older
than that window, archive them to the approved long-term store, verify the
archive checksum, and then drop the detached partition. The archive manifest
must retain the partition name, date range, row count, byte size, and checksum.
Deletion is not performed until the archive verification succeeds.

The default partition is retained permanently as a safety net. Maintenance
creates the current and future monthly partitions and moves rows from the
default partition into the matching month before reattaching it. Rows still in
the default partition are outside the maintenance horizon and produce a
warning for operator review.
