# SystemLink DataFrame API (Data Tables) Guide

This guide covers the SystemLink DataFrame API (`/nidataframe/v1`), which provides access to Data Tables - a tabular data storage system with support for filtering, sorting, and pagination.

---

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Base Endpoint** | `/nidataframe/v1` |
| **Authentication** | `X-NI-API-KEY` header |
| **Data Read** | POST `/tables/{id}/query-data` |
| **List Tables** | POST `/query-tables` or GET `/tables` |
| **Rate Limit** | Built-in (60 calls/min in client) |

---

## Table of Contents

1. [Key Concepts](#key-concepts)
2. [API Endpoints](#api-endpoints)
3. [Using DataFrameClient](#using-dataframeclient)
4. [Query Data with Filters](#query-data-with-filters)
5. [Pagination for Large Tables](#pagination-for-large-tables)
6. [Type Conversion](#type-conversion)
7. [Working Examples](#working-examples)
8. [Common Issues](#common-issues)

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Tables** | Named data containers with columns (schema) and rows (data) |
| **Workspaces** | Logical containers; each table belongs to one workspace |
| **Columns** | Typed schema definition (STRING, INT32, FLOAT32, TIMESTAMP, etc.) |
| **query-data** | POST endpoint for reading data with filters and pagination |
| **continuationToken** | Opaque token for paginating through large datasets |

### Table Properties

| Property | Description |
|----------|-------------|
| `id` | Unique table identifier (24-char hex string) |
| `name` | Human-readable table name |
| `workspace` | Workspace ID the table belongs to |
| `columns` | Array of column definitions with `name`, `dataType`, `columnType` |
| `rowCount` | Total number of rows in the table |
| `createdAt` | Table creation timestamp |
| `updatedAt` | Last modification timestamp |

---

## API Endpoints

### Working Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tables` | List all tables (with optional query params) |
| POST | `/query-tables` | Query tables with filters |
| GET | `/tables/{id}` | Get table metadata by ID |
| POST | `/tables/{id}/query-data` | **Read data** with filters/pagination |
| POST | `/tables` | Create a new table |
| DELETE | `/tables/{id}` | Delete a table |

### Non-Working Endpoints (500 Errors)

| Method | Endpoint | Error |
|--------|----------|-------|
| GET | `/tables/{id}/data` | `DataFrame.RowDataReaderError` |
| POST | `/export-data` | `DataFrame.RowDataReaderError` |

> **Note:** Always use `POST /tables/{id}/query-data` for reading table data.

---

## Using DataFrameClient

### Installation

The `DataFrameClient` is included in `systemlink_client.py`. Required dependencies:

```bash
pip install requests pandas tenacity ratelimit python-dotenv
```

### Basic Usage

```python
from systemlink_client import get_dataframe_client

# Create client (reads from .env or environment variables)
df_client = get_dataframe_client()

# List all tables
tables = df_client.query_tables()
for t in tables:
    print(f"{t['name']}: {t['rowCount']} rows")

# Get table by name (with workspace filter)
table = df_client.get_table_by_name(
    name="AnomalyScore",
    workspace="ee940aa2-05d3-4585-a822-52f7234a5207"
)

# Read all data as pandas DataFrame
df = df_client.to_dataframe(table["id"])
print(df.head())

# Get statistical summary
summary = df_client.summary(table["id"])
print(f"Total rows: {summary['total_rows']}")
print(f"Columns: {summary['columns']}")
```

### Client Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `query_tables(workspace=None)` | List tables, optionally filtered by workspace | `List[Dict]` |
| `get_table(table_id)` | Get table metadata by ID | `Dict` |
| `get_table_by_name(name, workspace=None)` | Find table by name | `Dict` or `None` |
| `query_data(table_id, take, skip, filters, order_by, token)` | Query data with parameters | `Dict` with `frame`, `totalRowCount`, `continuationToken` |
| `iter_table_data(table_id, batch_size=2000)` | Generator for batch reading | `Iterator[Dict]` |
| `get_all_data(table_id, batch_size=2000)` | Fetch all rows at once | `Dict` with `columns` and `rows` |
| `to_dataframe(table_id)` | Convert table to pandas DataFrame | `pd.DataFrame` |
| `summary(table_id)` | Get statistical summary | `Dict` |

---

## Query Data with Filters

### Request Format

```python
data = df_client.query_data(
    table_id="675aa2adfe50d4698153e947",
    take=1000,
    filters=[
        {"column": "Status", "operation": "EQUALS", "value": "PASS"},
        {"column": "Temperature", "operation": "GREATER_THAN", "value": "25"}
    ],
    order_by=[
        {"column": "StartTime", "descending": True}
    ]
)
```

### Filter Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `EQUALS` | Exact match | `{"column": "Status", "operation": "EQUALS", "value": "PASS"}` |
| `NOT_EQUALS` | Not equal | `{"column": "Type", "operation": "NOT_EQUALS", "value": "None"}` |
| `GREATER_THAN` | > comparison | `{"column": "Score", "operation": "GREATER_THAN", "value": "0.5"}` |
| `LESS_THAN` | < comparison | `{"column": "Count", "operation": "LESS_THAN", "value": "100"}` |
| `GREATER_THAN_EQUALS` | >= comparison | `{"column": "Value", "operation": "GREATER_THAN_EQUALS", "value": "10"}` |
| `LESS_THAN_EQUALS` | <= comparison | `{"column": "Value", "operation": "LESS_THAN_EQUALS", "value": "100"}` |
| `CONTAINS` | String contains | `{"column": "Name", "operation": "CONTAINS", "value": "test"}` |
| `STARTS_WITH` | String prefix | `{"column": "ID", "operation": "STARTS_WITH", "value": "ESS"}` |

### Order By

```python
order_by = [
    {"column": "StartTime", "descending": True},   # Sort by time, newest first
    {"column": "Name", "descending": False}        # Then by name ascending
]
```

### Response Format

```json
{
    "frame": {
        "columns": [
            {"name": "UUID", "dataType": "STRING"},
            {"name": "StartTime", "dataType": "TIMESTAMP"},
            {"name": "Score", "dataType": "FLOAT32"}
        ],
        "data": [
            ["abc-123", "2024-01-15T10:30:00Z", "0.95"],
            ["def-456", "2024-01-14T09:15:00Z", "0.87"]
        ]
    },
    "totalRowCount": 16704,
    "continuationToken": "eyJza..."
}
```

> **Note:** All values in `data` are returned as strings, regardless of column `dataType`.

---

## Pagination for Large Tables

### Using Iterator (Recommended)

```python
# Memory-efficient iteration through large tables
total_processed = 0
for batch in df_client.iter_table_data(table_id, batch_size=2000):
    for row in batch["data"]:
        process(row)
    total_processed += len(batch["data"])
    print(f"Processed {total_processed}/{batch['totalRowCount']} rows")
```

### Manual Pagination with continuationToken

```python
token = None
all_rows = []

while True:
    result = df_client.query_data(
        table_id=table_id,
        take=2000,
        continuation_token=token
    )
    
    all_rows.extend(result["data"])
    token = result.get("continuationToken")
    
    if not token:
        break

print(f"Fetched {len(all_rows)} rows total")
```

### Batch Size Recommendations

| Table Size | Recommended Batch Size |
|------------|------------------------|
| < 1,000 rows | 1000 (single request) |
| 1,000 - 10,000 rows | 2000 |
| 10,000 - 100,000 rows | 5000 |
| > 100,000 rows | 5000-10000 with streaming |

---

## Type Conversion

The API returns all values as strings. Convert to proper types using pandas:

### Automatic Detection

```python
df = df_client.to_dataframe(table_id)

# pandas may auto-detect some types, but often needs help
print(df.dtypes)
```

### Explicit Conversion

```python
import pandas as pd

df = df_client.to_dataframe(table_id)

# Numeric columns
numeric_cols = ['Score', 'Temperature', 'Count', 'MAE', 'RMSE']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Datetime columns
datetime_cols = ['StartTime', 'EndTime', 'CreatedAt']
for col in datetime_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# Boolean columns (stored as "True"/"False" strings)
bool_cols = ['IsValid', 'Passed']
for col in bool_cols:
    if col in df.columns:
        df[col] = df[col].map({'True': True, 'False': False, 'true': True, 'false': False})
```

### Column Data Types

| API DataType | Python/Pandas Type | Conversion |
|--------------|-------------------|------------|
| `STRING` | `object` | No conversion needed |
| `INT32` | `int64` | `pd.to_numeric(df[col], errors='coerce').astype('Int64')` |
| `INT64` | `int64` | `pd.to_numeric(df[col], errors='coerce').astype('Int64')` |
| `FLOAT32` | `float64` | `pd.to_numeric(df[col], errors='coerce')` |
| `FLOAT64` | `float64` | `pd.to_numeric(df[col], errors='coerce')` |
| `TIMESTAMP` | `datetime64[ns]` | `pd.to_datetime(df[col], errors='coerce')` |
| `BOOL` | `bool` | `df[col].map({'True': True, 'False': False})` |

---

## Working Examples

### Example 1: Read Table and Analyze

```python
from systemlink_client import get_dataframe_client
import pandas as pd

df_client = get_dataframe_client()

# Find the table
table = df_client.get_table_by_name("AnomalyScore", workspace="your-workspace-id")

# Read all data
df = df_client.to_dataframe(table["id"])

# Convert numeric columns
for col in ['MAE_linear', 'RMSE_linear', 'MAE_cubic']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Analyze
print(f"Total rows: {len(df)}")
print(f"Pass rate: {(df['PassUSL'] == 'PASS').mean():.1%}")
print(f"Mean MAE: {df['MAE_linear'].mean():.4f}")
print(f"Unique products: {df['Product'].nunique()}")
```

### Example 2: Filter and Export

```python
from systemlink_client import get_dataframe_client

df_client = get_dataframe_client()

# Query with filters
data = df_client.query_data(
    table_id="675aa2adfe50d4698153e947",
    take=10000,
    filters=[
        {"column": "PassUSL", "operation": "EQUALS", "value": "FAIL"}
    ],
    order_by=[{"column": "StartTime", "descending": True}]
)

# Convert to DataFrame
columns = [c["name"] for c in data["columns"]]
df = pd.DataFrame(data["data"], columns=columns)

# Export to CSV
df.to_csv("failures.csv", index=False)
print(f"Exported {len(df)} failure records")
```

### Example 3: Compare Tables

```python
from systemlink_client import get_dataframe_client

df_client = get_dataframe_client()
workspace = "ee940aa2-05d3-4585-a822-52f7234a5207"

# Get both tables
tables = df_client.query_tables(workspace=workspace)
for t in tables:
    summary = df_client.summary(t["id"])
    print(f"\n=== {t['name']} ===")
    print(f"Rows: {summary['total_rows']}")
    print(f"Columns: {len(summary['columns'])}")
    if summary['numeric_columns']:
        for col, stats in list(summary['numeric_columns'].items())[:3]:
            print(f"  {col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}")
```

### Example 4: Integration with Notification

```python
from systemlink_client import get_dataframe_client, get_notification_client
import pandas as pd

df_client = get_dataframe_client()
notif = get_notification_client()

# Get anomaly data
table = df_client.get_table_by_name("AnomalyScore", workspace="your-workspace-id")
df = df_client.to_dataframe(table["id"])

# Calculate failure rate
fail_count = (df['PassUSL'] == 'FAIL').sum()
total = len(df)
fail_rate = fail_count / total * 100

# Send alert if failure rate exceeds threshold
if fail_rate > 5.0:
    notif.send_email(
        to=["quality@example.com"],
        subject=f"Alert: Anomaly Failure Rate {fail_rate:.1f}%",
        body=f"""
Anomaly Detection Alert
=======================
Total Records: {total}
Failures: {fail_count}
Failure Rate: {fail_rate:.1f}%

Please review the anomaly detection results.
        """
    )
```

---

## Common Issues

### Issue: 500 Error on Data Read

**Symptom:**
```
requests.exceptions.HTTPError: 500: {"error": {"code": "DataFrame.RowDataReaderError"}}
```

**Cause:** Using wrong endpoint (`GET /data` or `POST /export-data`)

**Solution:** Use `POST /tables/{id}/query-data` endpoint:
```python
# Wrong
response = session.get(f"/nidataframe/v1/tables/{id}/data")

# Correct
response = session.post(f"/nidataframe/v1/tables/{id}/query-data", json={"take": 1000})
```

### Issue: All Values Are Strings

**Cause:** API returns all data as strings

**Solution:** Convert after fetching:
```python
df = df_client.to_dataframe(table_id)
df['NumericCol'] = pd.to_numeric(df['NumericCol'], errors='coerce')
```

### Issue: Table Not Found

**Symptom:** `get_table_by_name()` returns `None`

**Solution:** Check workspace filter:
```python
# Without workspace - searches all
table = df_client.get_table_by_name("MyTable")

# With workspace - more specific
table = df_client.get_table_by_name("MyTable", workspace="your-workspace-id")
```

### Issue: Memory Error on Large Tables

**Symptom:** `MemoryError` when loading large tables

**Solution:** Use iterator instead of loading all at once:
```python
# Instead of this (loads all into memory)
df = df_client.to_dataframe(table_id)

# Do this (processes in batches)
for batch in df_client.iter_table_data(table_id, batch_size=5000):
    process_batch(batch["data"])
```

---

## See Also

- [API_WRAPPER_GUIDE.md](API_WRAPPER_GUIDE.md) - General client library documentation
- [systemlink_client.py](systemlink_client.py) - Source code with DataFrameClient implementation
- [NOTIFICATION_API_GUIDE.md](NOTIFICATION_API_GUIDE.md) - Send email reports with analysis results
- [ASSET_MANAGEMENT_GUIDE.md](ASSET_MANAGEMENT_GUIDE.md) - Query asset data
