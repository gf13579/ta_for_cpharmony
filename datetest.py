# datetest.py
from datetime import datetime, timezone
earliest_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

## Need to do time maths now - subtract 2 days etc.

print(earliest_time)