# TDMS File Reader Examples

This folder contains examples for reading and analyzing **TDMS (Technical Data Management Streaming)** files using Python. TDMS is a binary file format developed by National Instruments, commonly used for storing measurement and test data from LabVIEW, TestStand, and other NI software.

## Scripts

| Script | Purpose |
|--------|---------|
| [read_tdms.py](read_tdms.py) | General-purpose TDMS reader with CLI |
| [tdms_test_overview.py](tdms_test_overview.py) | Power device test analyzer with automatic summary |

## Overview

The `read_tdms.py` script provides a comprehensive tool for:
- Exploring TDMS file structure (groups, channels, properties)
- Extracting and analyzing channel data
- Computing statistics on measurement data
- Exporting data to CSV format

## TDMS File Structure

TDMS files have a hierarchical structure:

```
TDMS File
├── File Properties (metadata about the entire file)
├── Group 1
│   ├── Group Properties
│   ├── Channel 1 (data array + properties)
│   ├── Channel 2 (data array + properties)
│   └── ...
├── Group 2
│   ├── Group Properties
│   ├── Channel 1
│   └── ...
└── ...
```

## Requirements

Install the required packages:

```bash
pip install nptdms numpy pandas click colorama
```

Or with the requirements file:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage - Show File Summary

```bash
python read_tdms.py path/to/file.tdms
```

Output:
```
============================================================
TDMS File: example.tdms
============================================================
  Size: 38.75 MB
  Groups: 2
  Total Channels: 9
  Total Data Points: 5,062,516

File Properties
----------------------------------------
  Test Name: LM_Validation_Program
  Device: TPS544B27
  Start Time: 1/26/2024 3:05:52 PM

Groups and Channels
----------------------------------------
  📁 HDO8k
     └─ PVIN (625,002 pts, float64)
     └─ VOUT (625,002 pts, float64)
     └─ IL (625,002 pts, float64)
     ...
```

### List Groups

```bash
python read_tdms.py file.tdms --groups
```

### List All Channels

```bash
python read_tdms.py file.tdms --channels
```

### Show All Properties

```bash
python read_tdms.py file.tdms --properties
```

### Show Group Details

```bash
python read_tdms.py file.tdms --group "HDO8k"
```

### Show Channel Details with Sample Data

```bash
python read_tdms.py file.tdms --channel "HDO8k/VOUT" --samples 20
```

### Show Statistics for All Channels

```bash
python read_tdms.py file.tdms --stats
```

### Export to CSV

```bash
# Export all groups (creates separate CSV per group)
python read_tdms.py file.tdms --export output.csv

# Export specific group
python read_tdms.py file.tdms --group "HDO8k" --export hdo8k_data.csv
```

## Using as a Library

You can also import the `TdmsReader` class in your own scripts:

```python
from read_tdms import TdmsReader

# Open a TDMS file
reader = TdmsReader("path/to/file.tdms")

# Get file summary
summary = reader.get_summary()
print(f"Total channels: {summary['total_channels']}")

# Get list of groups
groups = reader.get_groups()

# Get channels in a group
channels = reader.get_channels("HDO8k")

# Get channel data as numpy array
data = reader.get_channel_data("HDO8k", "VOUT")
print(f"Mean voltage: {data.mean():.3f} V")

# Get channel info with statistics
info = reader.get_channel_info("HDO8k", "VOUT")
print(f"Min: {info['statistics']['min']}")
print(f"Max: {info['statistics']['max']}")

# Get file properties
props = reader.get_file_properties()
print(f"Test: {props.get('Test Name')}")

# Export to CSV
reader.export_to_csv("output.csv")
```

## Working with Channel Data

### Basic Analysis

```python
import numpy as np
from read_tdms import TdmsReader

reader = TdmsReader("file.tdms")

# Get voltage data
vout = reader.get_channel_data("HDO8k", "VOUT")

# Basic statistics
print(f"Samples: {len(vout)}")
print(f"Mean: {np.mean(vout):.4f} V")
print(f"Std Dev: {np.std(vout):.4f} V")
print(f"Peak-to-Peak: {np.ptp(vout):.4f} V")
```

### Time Series Analysis

```python
import numpy as np

# If the file has time data
time = reader.get_channel_data("HDO8k", "Time")
voltage = reader.get_channel_data("HDO8k", "VOUT")

# Calculate sample rate
sample_rate = 1 / np.mean(np.diff(time))
print(f"Sample Rate: {sample_rate/1e6:.2f} MHz")
```

### Plotting Data

```python
import matplotlib.pyplot as plt
from read_tdms import TdmsReader

reader = TdmsReader("file.tdms")
vout = reader.get_channel_data("HDO8k", "VOUT")

plt.figure(figsize=(12, 4))
plt.plot(vout[:10000])  # Plot first 10k samples
plt.xlabel("Sample")
plt.ylabel("Voltage (V)")
plt.title("VOUT Measurement")
plt.grid(True)
plt.show()
```

## Common Use Cases

### 1. Quick File Inspection

```bash
# See what's in a TDMS file
python read_tdms.py unknown_file.tdms
```

### 2. Extract Specific Measurements

```python
reader = TdmsReader("test_results.tdms")

# Get all voltage measurements
for group in reader.get_groups():
    for channel in reader.get_channels(group):
        if "VOLT" in channel.upper() or "V" in channel:
            data = reader.get_channel_data(group, channel)
            print(f"{group}/{channel}: {data.mean():.3f} V")
```

### 3. Batch Processing Multiple Files

```python
from pathlib import Path
from read_tdms import TdmsReader

# Process all TDMS files in a directory
for tdms_file in Path("data/").glob("*.tdms"):
    reader = TdmsReader(str(tdms_file))
    summary = reader.get_summary()
    print(f"{tdms_file.name}: {summary['total_data_points']:,} points")
```

### 4. Compare Channels Across Files

```python
results = []
for tdms_file in Path("data/").glob("*.tdms"):
    reader = TdmsReader(str(tdms_file))
    vout = reader.get_channel_data("HDO8k", "VOUT")
    results.append({
        'file': tdms_file.name,
        'mean': vout.mean(),
        'std': vout.std(),
    })

# Create comparison DataFrame
import pandas as pd
df = pd.DataFrame(results)
print(df)
```

## TDMS Properties Reference

Common properties you might find in TDMS files:

| Property | Description |
|----------|-------------|
| `name` | Channel or group name |
| `NI_ArrayColumn` | Column index for 2D arrays |
| `NI_ChannelLength` | Number of samples |
| `NI_DataType` | Numeric data type |
| `unit_string` | Engineering unit (V, A, Hz, etc.) |
| `wf_increment` | Time step for waveform data |
| `wf_samples` | Number of waveform samples |
| `wf_start_offset` | Waveform start time offset |

## Troubleshooting

### Memory Issues with Large Files

For very large TDMS files, use the file in read mode and process data in chunks:

```python
from nptdms import TdmsFile

# Read without loading all data into memory
with TdmsFile.open("large_file.tdms") as tdms_file:
    channel = tdms_file["Group"]["Channel"]
    
    # Process in chunks
    chunk_size = 100000
    for i in range(0, len(channel), chunk_size):
        chunk = channel[i:i+chunk_size]
        # Process chunk...
```

### Encoding Issues with Properties

Some TDMS files may have properties with special characters:

```python
props = reader.get_file_properties()
for key, value in props.items():
    try:
        print(f"{key}: {value}")
    except UnicodeEncodeError:
        print(f"{key}: [contains special characters]")
```

## Related Resources

- [nptdms Documentation](https://nptdms.readthedocs.io/)
- [TDMS File Format Specification](https://www.ni.com/en-us/support/documentation/supplemental/06/the-ni-tdms-file-format.html)
- [NI SystemLink File Service](https://www.ni.com/docs/en-US/bundle/systemlink-enterprise/page/file-service.html)

---

## Test Overview Generator (tdms_test_overview.py)

The `tdms_test_overview.py` script is specialized for power device validation test data. It automatically:
- Identifies the device under test (e.g., TPS544B27 DC-DC converter)
- Extracts test conditions (voltage, temperature, protection settings)
- Analyzes measurement channels for anomalies
- Determines if protection tests passed or failed
- Generates a human-readable summary

### Usage

```bash
# Generate test overview
python tdms_test_overview.py test_data.tdms

# Output as Markdown
python tdms_test_overview.py test_data.tdms --markdown -o report.md

# Output as JSON
python tdms_test_overview.py test_data.tdms --json -o report.json

# Batch process multiple files
python tdms_test_overview.py *.tdms --batch
```

### Example Output

```
══════════════════════════════════════════════════════════════════════
  Test Overview: VAL_OCP_test_data.tdms
══════════════════════════════════════════════════════════════════════

▶ Device Under Test
──────────────────────────────────────────────────
  Device: TPS544B27 - DC-DC Step-Down Converter (20A Synchronous Buck)
  Unit/Serial: 35_Brd2B
  Lot: NA

▶ Test Conditions
──────────────────────────────────────────────────
  Test Type: Over-Current Protection
  Input Voltage: 5.0V
  Output Voltage: 1.8V
  Temperature: 25.0°C

▶ Test Outcome
──────────────────────────────────────────────────
  Status: PASS
  Fault Detected: Yes
  Observations:
    • Output voltage collapsed from 1.8V to -0.835V
    • Protection mechanism activated as expected - TEST PASSED

▶ Summary
──────────────────────────────────────────────────
The TPS544B27 was tested at 25°C with 5V input and 1.8V output to verify
its over-current protection response. During the test, a fault event was
triggered, causing the output voltage to drop, demonstrating the protection
circuit activating to shut off the output.
```

### Supported Test Types

| Test Type | Description | Pass Criteria |
|-----------|-------------|---------------|
| OCP | Over-Current Protection | Fault triggers when current exceeds threshold |
| OVP | Over-Voltage Protection | Fault triggers when voltage exceeds threshold |
| UVP | Under-Voltage Protection | Fault triggers when voltage drops below threshold |
| PSRR | Power Supply Rejection Ratio | Measures ripple attenuation |
| EFFICIENCY | Efficiency Measurement | Output/Input power ratio |

### Supported Device Families

- **TPS544/546/548** - DC-DC Synchronous Buck Converters
- **LM5xxx** - DC-DC Switching Regulators
- **LMZxxxx** - DC-DC Power Modules

### Using as a Library

```python
from tdms_test_overview import PowerDeviceAnalyzer

# Analyze a test file
analyzer = PowerDeviceAnalyzer("test_data.tdms")

# Get device info
device = analyzer.get_device_info()
print(f"Device: {device['name']} - {device['description']}")

# Get test conditions
test = analyzer.get_test_conditions()
print(f"Test: {test['test_type']} at {test['temperature']}°C")

# Get protection settings
protection = analyzer.get_protection_settings()
print(f"OC Fault Threshold: {protection['ocf_threshold']}")

# Get test outcome
outcome = analyzer.get_test_outcome()
print(f"Result: {outcome['status']}")
for obs in outcome['observations']:
    print(f"  - {obs}")

# Get complete overview as dictionary
overview = analyzer.generate_overview()

# Access the auto-generated summary text
print(overview['summary'])
```

---

## License

See the repository [LICENSE](../../../LICENSE) file.
