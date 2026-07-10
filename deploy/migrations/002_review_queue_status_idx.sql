-- Review queue: index pending FIFO scans + status filters.
-- Ship: advoi-memory-review-queue-pg-01
-- Table created in 000_baseline_tables.sql; this is additive only.

CREATE INDEX IF NOT EXISTS review_queue_status_created_at_idx
    ON review_queue (status, created_at ASC);
