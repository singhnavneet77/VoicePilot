# Data

The application does not require external data for the demo.

For organizer-provided data, use a CSV containing:

```text
lead_id,variant,meeting_fixed,call_duration_sec,timestamp
```

Example:

```csv
lead_id,variant,meeting_fixed,call_duration_sec,timestamp
L001,A,1,48,2026-10-08T10:00:00
L002,B,0,71,2026-10-08T10:01:00
```

Do not claim causal lift from historical observational data unless the experimental design supports it.
