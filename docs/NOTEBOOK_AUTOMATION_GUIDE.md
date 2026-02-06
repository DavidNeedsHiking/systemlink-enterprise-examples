# SystemLink Notebook Automation Guide

A comprehensive guide for creating and using automated Jupyter notebooks in NI SystemLink Enterprise.

**Last Updated:** February 6, 2026  
**Applies to:** SystemLink Enterprise 2024+

---

## Table of Contents

1. [Quick Start (Users)](#quick-start-users)
2. [Creating Automated Notebooks](#creating-automated-notebooks)
   - [Understanding the Parameters Cell](#understanding-the-parameters-cell)
   - [Defining Inputs (Parameters)](#defining-inputs-parameters)
   - [Defining Outputs (Scrapbook)](#defining-outputs-scrapbook)
3. [Complete Examples](#complete-examples)
4. [Reference](#reference)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start (Users)

> **Audience:** Test Engineers, Technicians, Validation Engineers

If you're running an existing automated notebook and need to modify parameters:

### Finding Parameters in a Notebook

1. Look for a cell with the comment `#parameters` at the top
2. The cell will have a **tag** `parameters` visible in the cell metadata
3. Parameters are defined as Python variables with default values

### Example Parameters Cell

```python
#parameters
file_ids = []           # List of file IDs to process
part_number = ""        # Part number for the analysis
discipline = "Thermal"  # Analysis discipline
```

### How Parameters Are Passed

When SystemLink executes the notebook:
1. It reads the parameter definitions from cell metadata
2. Injects new values based on your workflow configuration
3. Executes the notebook with those values

**You don't modify parameters manually** - SystemLink handles this through:
- Test Plan automations
- Work Item automations
- Scheduled executions
- Manual execution via Notebook Execution API

---

## Creating Automated Notebooks

> **Audience:** Application Engineers, Data Scientists, Solution Architects

### Understanding the Parameters Cell

The parameters cell is the **single source of truth** for both inputs AND outputs. It uses:

| Technology | Purpose |
|------------|---------|
| **Papermill** | Parameter injection at runtime |
| **SystemLink Metadata** | UI integration, type definitions |
| **Scrapbook** | Output capture and retrieval |

### The Metadata Structure

The parameters cell has this metadata structure:

```json
{
  "tags": ["parameters"],
  "papermill": {
    "parameters": {
      "file_ids": [],
      "part_number": ""
    }
  },
  "systemlink": {
    "version": 2,
    "interfaces": ["ni-files"],
    "parameters": [...],
    "outputs": [...]
  }
}
```

---

### Defining Inputs (Parameters)

#### Step 1: Create the Parameters Cell

Add a code cell with `#parameters` comment:

```python
#parameters
file_ids = []
part_number = ""
notebook_id = ""
```

#### Step 2: Add the `parameters` Tag

In VS Code:
1. Click on the cell
2. Open cell metadata (wrench icon or `...` menu)
3. Add tag: `parameters`

#### Step 3: Define SystemLink Metadata

Add to cell metadata:

```json
{
  "systemlink": {
    "version": 2,
    "interfaces": ["ni-files"],
    "parameters": [
      {
        "id": "file_ids",
        "display_name": "File IDs",
        "type": "string[]"
      },
      {
        "id": "part_number",
        "display_name": "Part Number",
        "type": "string"
      }
    ]
  }
}
```

#### Supported Parameter Types

| Type | Python | Description |
|------|--------|-------------|
| `string` | `str` | Single text value |
| `string[]` | `list[str]` | List of strings (e.g., file_ids) |
| `number` | `int`, `float` | Numeric value |
| `boolean` | `bool` | True/False |

#### Common Interfaces

| Interface | When to Use |
|-----------|-------------|
| `ni-files` | Notebook processes files from File Service |
| `ni-testmonitor` | Notebook processes test results |
| `ni-assets` | Notebook processes assets |

---

### Defining Outputs (Scrapbook)

Outputs are defined in **two places**:
1. **Metadata** - declares what outputs exist (for SystemLink UI)
2. **Code** - uses scrapbook to capture actual values

#### Step 1: Declare Outputs in Metadata

Add to the parameters cell metadata:

```json
{
  "systemlink": {
    "outputs": [
      {
        "id": "result_count",
        "display_name": "Results Processed",
        "type": "scalar"
      },
      {
        "id": "error_info",
        "display_name": "Error Details",
        "type": "dataframe"
      }
    ]
  }
}
```

#### Step 2: Import Scrapbook

```python
import scrapbook as sb
```

#### Step 3: Glue Results at End of Notebook

Create a cell (typically at the end) to output results:

```python
# Define output
result = [
    {
        'id': 'result_count',
        'type': 'scalar',
        'data': processed_count
    },
    {
        'id': 'error_info',
        'type': 'data_frame',
        'data': {
            'columns': pd.io.json.build_table_schema(df, index=False)['fields'],
            'values': df.values.tolist()
        }
    }
]
sb.glue('result', result)
```

#### Supported Output Types

| Type | Use Case | Data Format |
|------|----------|-------------|
| `scalar` | Single value | Direct value (string, number, boolean) |
| `string[]` | List of values | Python list |
| `dataframe` | Tabular data | `{columns: [...], values: [[...]]}` |

---

## Complete Examples

### Example 1: Input Only (File Processing)

**Use Case:** Process uploaded TDMS files, no outputs needed

#### Parameters Cell

```python
#parameters
file_ids = []  # List of file IDs to process
```

#### Metadata

```json
{
  "tags": ["parameters"],
  "papermill": {
    "parameters": {
      "file_ids": []
    }
  },
  "systemlink": {
    "version": 2,
    "interfaces": ["ni-files"],
    "parameters": [
      {
        "id": "file_ids",
        "display_name": "File IDs",
        "type": "string[]"
      }
    ]
  }
}
```

---

### Example 2: Input and Output (Analysis with Results)

**Use Case:** Analyze files and return summary statistics

#### Parameters Cell

```python
#parameters
file_ids = []
part_number = ""
discipline = "Analysis"
```

#### Metadata

```json
{
  "tags": ["parameters"],
  "papermill": {
    "parameters": {
      "file_ids": [],
      "part_number": "",
      "discipline": "Analysis"
    }
  },
  "systemlink": {
    "version": 2,
    "interfaces": ["ni-files"],
    "parameters": [
      {
        "id": "file_ids",
        "display_name": "File IDs",
        "type": "string[]"
      },
      {
        "id": "part_number",
        "display_name": "Part Number",
        "type": "string"
      },
      {
        "id": "discipline",
        "display_name": "Discipline",
        "type": "string"
      }
    ],
    "outputs": [
      {
        "id": "files_processed",
        "display_name": "Files Processed",
        "type": "scalar"
      },
      {
        "id": "analysis_results",
        "display_name": "Analysis Results",
        "type": "dataframe"
      }
    ]
  }
}
```

#### Output Cell (at end of notebook)

```python
import scrapbook as sb
import pandas as pd

# Prepare results
result = [
    {
        'id': 'files_processed',
        'type': 'scalar',
        'data': len(file_ids)
    },
    {
        'id': 'analysis_results',
        'type': 'data_frame',
        'data': {
            'columns': pd.io.json.build_table_schema(results_df, index=False)['fields'],
            'values': results_df.values.tolist()
        }
    }
]
sb.glue('result', result)
```

---

### Example 3: Real-World Pattern (TDMS Anomaly Score)

Based on `TDMS_CalculateAnomalyScore_Demo.ipynb`:

#### Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `file_ids` | `string[]` | TDMS files to analyze |
| `part_number` | `string` | Part identifier |
| `notebook_id` | `string` | Self-reference for logging |
| `discipline` | `string` | Analysis category |

#### Outputs

| Output | Type | Purpose |
|--------|------|---------|
| `Test Result ID` | `scalar` | Created test result ID |
| `Data Table ID` | `scalar` | Created data table ID |
| `error_info` | `dataframe` | Error details if any |

---

## Reference

### Complete Metadata Schema

```json
{
  "tags": ["parameters"],
  "editable": true,
  "slideshow": {"slide_type": ""},
  "papermill": {
    "parameters": {
      "<param_id>": "<default_value>"
    }
  },
  "systemlink": {
    "version": 2,
    "interfaces": ["<interface_name>"],
    "parameters": [
      {
        "id": "<param_id>",
        "display_name": "<UI Label>",
        "type": "<type>"
      }
    ],
    "outputs": [
      {
        "id": "<output_id>",
        "display_name": "<UI Label>",
        "type": "<type>"
      }
    ]
  }
}
```

### Type Reference

#### Parameter Types

| Type | JSON | Python | Example |
|------|------|--------|---------|
| String | `"string"` | `str` | `"part_number": "ABC123"` |
| String Array | `"string[]"` | `list` | `"file_ids": ["id1", "id2"]` |
| Number | `"number"` | `int`/`float` | `"threshold": 0.95` |
| Boolean | `"boolean"` | `bool` | `"verbose": true` |

#### Output Types

| Type | Format | Use Case |
|------|--------|----------|
| `scalar` | Direct value | Counts, IDs, status |
| `string[]` | List | Multiple IDs, names |
| `dataframe` | `{columns, values}` | Tabular results |

### Scrapbook Output Format

```python
result = [
    {
        'id': '<output_id>',        # Must match metadata
        'type': '<scalar|data_frame|string[]>',
        'data': <value>
    }
]
sb.glue('result', result)
```

### DataFrame Output Format

```python
{
    'id': 'my_dataframe',
    'type': 'data_frame',
    'data': {
        'columns': pd.io.json.build_table_schema(df, index=False)['fields'],
        'values': df.values.tolist()
    }
}
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Parameters not injected | Missing `parameters` tag | Add tag to cell metadata |
| Outputs not captured | `sb.glue` not called | Add scrapbook glue at end of notebook |
| Type mismatch | Parameter type doesn't match Python variable | Ensure consistency between metadata and code |
| Output not visible in UI | Output ID mismatch | Ensure `id` in scrapbook matches metadata `id` |

### Debugging Tips

1. **Check cell has correct tag:**
   ```python
   # In VS Code, verify "parameters" tag is visible
   ```

2. **Validate JSON metadata:**
   ```python
   import json
   metadata = {...}  # Your metadata
   json.dumps(metadata)  # Will error if invalid
   ```

3. **Test scrapbook locally:**
   ```python
   import scrapbook as sb
   sb.glue('test', {'value': 42})
   # Check notebook output for glued data
   ```

4. **Verify parameter types match:**
   ```python
   # Metadata says string[], code must use list
   file_ids = []  # ✓ Correct
   file_ids = ""  # ✗ Wrong - should be list
   ```

---

## Resources

- [Papermill Documentation](https://papermill.readthedocs.io/en/latest/usage-parameterize.html)
- [Scrapbook Documentation](https://nteract-scrapbook.readthedocs.io/)
- [SystemLink Enterprise Examples](https://github.com/ni/systemlink-enterprise-examples)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-06 | 1.0 | Initial release |
