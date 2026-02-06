# Server Configuration

This file documents the SystemLink Enterprise server and data sources used in this project.

---

## Server Information

| Property | Value |
|----------|-------|
| **Server Name** | NI Lifecycle Solutions Test Server |
| **API URL** | `https://test-api.lifecyclesolutions.ni.com` |
| **Web UI URL** | `https://test.lifecyclesolutions.ni.com` |
| **Swagger Docs** | `https://test-api.lifecyclesolutions.ni.com/niapis/` |
| **Environment** | Test/Development |
| **Last Verified** | 2026-02-06 |

### API Version Information

| API | Base Path | Version |
|-----|-----------|---------|
| Asset Management | `/niapm/v1` | v1 |
| Test Monitor | `/nitestmonitor/v2` | v2 |
| Notification | `/ninotification/v1` | v1 |
| DataFrame (Data Tables) | `/nidataframe/v1` | v1 |
| File | `/nifile/v1` | v1 |
| User | `/niuser/v1` | v1 |

---

## Data Tables

### AnomalyScore Tables

| Table Name | Table ID | Workspace | Created | Rows | Description |
|------------|----------|-----------|---------|------|-------------|
| AnomalyScore_pivot | `67b49b21c92e0cfc3e7ae85b` | `ee940aa2-05d3-4585-a822-52f7234a5207` | 2025-02-18 | 1,392 | Pivoted anomaly scores with Condition grouping |

### Key Columns (AnomalyScore_pivot)

| Column | Data Type | Description |
|--------|-----------|-------------|
| UUID | STRING | Unique identifier |
| Condition | INT32 | Test condition (0-7) |
| Error_MAE_control_linear_value | FLOAT32 | Mean absolute error metric |
| Error_MSE_* | FLOAT32 | Mean squared error metrics |
| AnomalyScore_* | FLOAT32 | Various anomaly score columns |

---

## Workspaces

| Workspace Name | Workspace ID | Purpose |
|----------------|--------------|---------|
| Main Analysis | `ee940aa2-05d3-4585-a822-52f7234a5207` | Primary data tables workspace |

---

## API Key Configuration

API keys are stored in `.env` (not committed to version control).

Required environment variables:
```bash
SYSTEMLINK_API_URL=https://test-api.lifecyclesolutions.ni.com
SYSTEMLINK_API_KEY=your-api-key-here
```

Generate API keys from: **SystemLink UI → Security → API Keys**

---

## Known Limitations

### DataFrame API

| Endpoint | Status | Notes |
|----------|--------|-------|
| POST `/tables/{id}/query-data` | ✅ Working | Use this for reading data |
| GET `/tables/{id}/data` | ❌ 500 Error | `DataFrame.RowDataReaderError` |
| POST `/export-data` | ❌ 500 Error | `DataFrame.RowDataReaderError` |

---

## Version History

| Date | Change |
|------|--------|
| 2026-02-06 | Initial documentation |
