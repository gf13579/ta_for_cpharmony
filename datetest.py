# datetest.py
from datetime import datetime, timezone, timedelta


current_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
earliest_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="milliseconds").replace("+00:00","Z")

# Required format for Sophos XDR queries: 2022-01-01T12:02:01.000Z

## Need to do time maths now - subtract 2 days etc.

print(f"current:  {current_time}")
print(f"earliest: {earliest_time}")

