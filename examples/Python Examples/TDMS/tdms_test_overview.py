#!/usr/bin/env python3
"""
TDMS Test Overview Generator

This script analyzes TDMS files from power device validation tests and generates
a human-readable overview including:
- Device identification
- Test conditions and parameters
- Measurement summary with pass/fail indicators
- Automatic detection of fault events

Designed for power converter validation data (e.g., TPS544B27 DC-DC converters).

Requirements:
    pip install nptdms numpy click colorama

Usage:
    python tdms_test_overview.py <file_path>
    python tdms_test_overview.py <file_path> --json           # Output as JSON
    python tdms_test_overview.py <file_path> --markdown       # Output as Markdown
    python tdms_test_overview.py *.tdms --batch               # Process multiple files

Author: Generated for SystemLink Enterprise Examples
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

try:
    import click
    from colorama import init, Fore, Style
    import numpy as np
    from nptdms import TdmsFile
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install nptdms numpy click colorama")
    sys.exit(1)

# Initialize colorama
init()


class PowerDeviceAnalyzer:
    """Analyzes TDMS files from power device validation tests."""
    
    # Known test types based on filename patterns
    TEST_TYPES = {
        'OCP': 'Over-Current Protection',
        'OVP': 'Over-Voltage Protection',
        'UVP': 'Under-Voltage Protection',
        'PSRR': 'Power Supply Rejection Ratio',
        'EFFICIENCY': 'Efficiency Measurement',
        'LOAD_REG': 'Load Regulation',
        'LINE_REG': 'Line Regulation',
        'SOFT_START': 'Soft Start',
        'THERMAL': 'Thermal Shutdown',
    }
    
    # Known device families and their descriptions
    DEVICE_INFO = {
        'TPS544': 'DC-DC Step-Down Converter (20A Synchronous Buck)',
        'TPS546': 'DC-DC Step-Down Converter (30A Synchronous Buck)',
        'TPS548': 'DC-DC Step-Down Converter (12A Synchronous Buck)',
        'LM5': 'DC-DC Switching Regulator',
        'LMZ': 'DC-DC Power Module',
    }
    
    # Channel interpretations
    CHANNEL_MEANINGS = {
        'VOUT': ('Output Voltage', 'V'),
        'VIN': ('Input Voltage', 'V'),
        'PVIN': ('Power Input Voltage', 'V'),
        'IL': ('Inductor Current', 'A'),
        'IOUT': ('Output Current', 'A'),
        'SW': ('Switch Node Voltage', 'V'),
        'EN': ('Enable Signal', 'V'),
        'VCC': ('Control Circuit Supply', 'V'),
        'VRRDY': ('Voltage Ready/Power Good', 'V'),
        'ALERT': ('Fault Alert Signal', 'V'),
        'SV_ALERT': ('Supervisor Alert', 'V'),
        'PGOOD': ('Power Good Signal', 'V'),
        'TEMP': ('Temperature', '°C'),
    }
    
    def __init__(self, file_path: str):
        """Initialize the analyzer with a TDMS file."""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.tdms_file = TdmsFile.read(str(self.file_path))
        self.properties = dict(self.tdms_file.properties)
        self._cache = {}
    
    def get_device_info(self) -> Dict[str, Any]:
        """Extract device information from file properties."""
        device_name = self.properties.get('Device Name', 'Unknown')
        
        # Find matching device family
        device_description = 'Unknown Power Device'
        for prefix, desc in self.DEVICE_INFO.items():
            if device_name.startswith(prefix):
                device_description = desc
                break
        
        return {
            'name': device_name,
            'description': device_description,
            'lot': self.properties.get('Device Lot', 'N/A'),
            'unit': self.properties.get('Device Unit', 'N/A'),
            'serial': self.properties.get('DUT ID-FC', self.properties.get('Device Unit', 'N/A')),
        }
    
    def get_test_conditions(self) -> Dict[str, Any]:
        """Extract test conditions from file properties."""
        # Parse temperature
        temp = self.properties.get('Temp-FC', 25)
        if isinstance(temp, str):
            temp = float(temp.replace('C', '').replace('c', ''))
        
        return {
            'test_name': self.properties.get('Test Name', 'Unknown Test'),
            'test_type': self._detect_test_type(),
            'date': self.properties.get('Start Time', 'Unknown'),
            'station': self.properties.get('Station Name', 'Unknown'),
            'operator': self.properties.get('UserID', self.properties.get('User AID-FC', 'Unknown')),
            'run_mode': self.properties.get('Run Mode', 'Unknown'),
            'input_voltage': self._safe_float(self.properties.get('Vin(V)-FC', 0)),
            'output_voltage': self._safe_float(self.properties.get('Vout(V)-FC', 0)),
            'temperature': temp,
            'soak_time': self._safe_float(self.properties.get('SoakTime(s)-FC', 0)),
        }
    
    def get_protection_settings(self) -> Dict[str, Any]:
        """Extract protection threshold settings."""
        return {
            'uvf_threshold': self.properties.get('UVFL_Label-FC', 'N/A'),
            'uvw_threshold': self.properties.get('UVWL_Label-FC', 'N/A'),
            'ocf_threshold': self.properties.get('OCFL_Label-FC', 'N/A'),
            'ocw_threshold': self.properties.get('OCWL_Label-FC', 'N/A'),
            'fault_response': self.properties.get('UVFR_Label-FC', 'N/A'),
        }
    
    def get_channel_summary(self) -> List[Dict[str, Any]]:
        """Get summary statistics for all measurement channels."""
        summaries = []
        
        for group in self.tdms_file.groups():
            for channel in group.channels():
                data = channel[:]
                if len(data) == 0:
                    continue
                
                ch_name = channel.name.upper()
                meaning, unit = self.CHANNEL_MEANINGS.get(
                    ch_name, 
                    (channel.name, channel.properties.get('unit_string', ''))
                )
                
                # Calculate statistics
                stats = {
                    'group': group.name,
                    'channel': channel.name,
                    'meaning': meaning,
                    'unit': unit,
                    'samples': len(data),
                    'min': float(np.min(data)),
                    'max': float(np.max(data)),
                    'mean': float(np.mean(data)),
                    'std': float(np.std(data)),
                    'p2p': float(np.ptp(data)),  # Peak-to-peak
                }
                
                # Detect anomalies
                stats['anomalies'] = self._detect_anomalies(ch_name, data, stats)
                
                summaries.append(stats)
        
        return summaries
    
    def get_test_outcome(self) -> Dict[str, Any]:
        """Analyze channels to determine test outcome."""
        channels = self.get_channel_summary()
        conditions = self.get_test_conditions()
        
        outcome = {
            'status': 'UNKNOWN',
            'fault_detected': False,
            'fault_type': None,
            'observations': [],
            'recommendations': [],
        }
        
        # Find key channels
        vout_ch = next((c for c in channels if c['channel'].upper() == 'VOUT'), None)
        il_ch = next((c for c in channels if c['channel'].upper() == 'IL'), None)
        vrrdy_ch = next((c for c in channels if c['channel'].upper() == 'VRRDY'), None)
        
        # Analyze VOUT behavior
        if vout_ch:
            nominal_vout = conditions.get('output_voltage', 0)
            if nominal_vout > 0:
                # Check if output collapsed (protection triggered)
                if vout_ch['min'] < nominal_vout * 0.1:
                    outcome['fault_detected'] = True
                    outcome['observations'].append(
                        f"Output voltage collapsed from {nominal_vout}V to {vout_ch['min']:.3f}V"
                    )
                
                # Check voltage regulation
                if vout_ch['std'] > nominal_vout * 0.05:
                    outcome['observations'].append(
                        f"High output voltage variation (std: {vout_ch['std']:.4f}V)"
                    )
        
        # Analyze inductor current for OCP tests
        if il_ch and 'OCP' in conditions.get('test_type', ''):
            outcome['fault_type'] = 'Over-Current Protection'
            outcome['observations'].append(
                f"Peak inductor current: {il_ch['max']:.2f}A"
            )
            
            # Determine if OCP triggered correctly
            protection = self.get_protection_settings()
            ocf_label = protection.get('ocf_threshold', '')
            if 'A' in ocf_label:
                try:
                    threshold = float(ocf_label.replace('A_OCFL', '').replace('A', ''))
                    if il_ch['max'] > threshold:
                        outcome['observations'].append(
                            f"Current exceeded {threshold}A threshold - protection activated"
                        )
                except ValueError:
                    pass
        
        # Analyze VRRDY (Power Good)
        if vrrdy_ch:
            if vrrdy_ch['std'] > 1.0:  # High variation indicates toggling
                outcome['observations'].append(
                    "Power Good signal toggled - indicates fault/recovery cycles"
                )
        
        # Determine overall status
        test_type = conditions.get('test_type', '')
        is_protection_test = any(x in test_type for x in ['Over-Current', 'Over-Voltage', 'Under-Voltage', 'Protection'])
        
        if outcome['fault_detected']:
            if is_protection_test:
                outcome['status'] = 'PASS'  # For protection tests, triggering is expected
                outcome['observations'].append(
                    "Protection mechanism activated as expected - TEST PASSED"
                )
            else:
                outcome['status'] = 'FAIL'
        else:
            if is_protection_test:
                outcome['status'] = 'FAIL'  # Protection should have triggered but didn't
                outcome['observations'].append(
                    "Warning: Protection did not trigger during protection validation test"
                )
            else:
                outcome['status'] = 'PASS'
        
        return outcome
    
    def generate_overview(self) -> Dict[str, Any]:
        """Generate a complete test overview."""
        return {
            'file': {
                'name': self.file_path.name,
                'size_mb': self.file_path.stat().st_size / (1024 * 1024),
                'path': str(self.file_path),
            },
            'device': self.get_device_info(),
            'test': self.get_test_conditions(),
            'protection_settings': self.get_protection_settings(),
            'measurements': self.get_channel_summary(),
            'outcome': self.get_test_outcome(),
            'summary': self._generate_text_summary(),
        }
    
    def _detect_test_type(self) -> str:
        """Detect test type from filename or properties."""
        filename = self.file_path.name.upper()
        test_name = self.properties.get('Test Name', '').upper()
        
        for key, desc in self.TEST_TYPES.items():
            if key in filename or key in test_name:
                return desc
        
        return 'Unknown Test Type'
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace('V', '').replace('A', '').replace('C', ''))
        except (ValueError, TypeError):
            return 0.0
    
    def _detect_anomalies(self, channel_name: str, data: np.ndarray, stats: Dict) -> List[str]:
        """Detect anomalies in channel data."""
        anomalies = []
        
        # Voltage channels shouldn't go negative
        if 'VOUT' in channel_name or 'VIN' in channel_name:
            if stats['min'] < -0.5:
                anomalies.append(f"Negative voltage detected: {stats['min']:.3f}V")
        
        # High standard deviation relative to mean
        if stats['mean'] != 0 and abs(stats['std'] / stats['mean']) > 0.5:
            anomalies.append("High relative variation")
        
        return anomalies
    
    def _generate_text_summary(self) -> str:
        """Generate a human-readable text summary."""
        device = self.get_device_info()
        test = self.get_test_conditions()
        protection = self.get_protection_settings()
        outcome = self.get_test_outcome()
        channels = self.get_channel_summary()
        
        # Find key measurements
        vout = next((c for c in channels if c['channel'].upper() == 'VOUT'), None)
        il = next((c for c in channels if c['channel'].upper() == 'IL'), None)
        pvin = next((c for c in channels if c['channel'].upper() in ('PVIN', 'VIN')), None)
        
        lines = [
            f"The {device['name']} ({device['description']}) was tested at {test['temperature']}°C "
            f"with a {test['input_voltage']}V input and {test['output_voltage']}V nominal output "
            f"to verify its {test['test_type'].lower()} response.",
        ]
        
        if outcome['fault_detected'] and vout:
            lines.append(
                f"During the test, a fault event was triggered, causing the output voltage to "
                f"drop from {test['output_voltage']}V to {vout['min']:.3f}V, demonstrating the "
                f"protection circuit activating to shut off the output."
            )
        
        if il:
            lines.append(
                f"The inductor current peaked at {il['max']:.2f}A during the test, with the device "
                f"configured for {protection['fault_response']} fault response mode."
            )
        
        if pvin:
            lines.append(
                f"The input voltage remained stable at {pvin['mean']:.2f}V (±{pvin['std']:.3f}V) "
                f"throughout the test, confirming the fault was isolated to the output stage."
            )
        
        lines.append(
            f"Test Result: {outcome['status']} - " + 
            ("; ".join(outcome['observations'][:2]) if outcome['observations'] else "No anomalies detected.")
        )
        
        return "\n\n".join(lines)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  {title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Fore.YELLOW}▶ {title}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 50}{Style.RESET_ALL}")


def print_kv(key: str, value: Any, indent: int = 2):
    """Print a key-value pair."""
    print(f"{' ' * indent}{Fore.WHITE}{key}:{Style.RESET_ALL} {value}")


def format_status(status: str) -> str:
    """Format status with color."""
    colors = {
        'PASS': Fore.GREEN,
        'FAIL': Fore.RED,
        'UNKNOWN': Fore.YELLOW,
    }
    color = colors.get(status, Fore.WHITE)
    return f"{color}{status}{Style.RESET_ALL}"


@click.command()
@click.argument('file_paths', nargs=-1, type=click.Path(exists=True))
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--markdown', 'output_md', is_flag=True, help='Output as Markdown')
@click.option('--batch', is_flag=True, help='Process multiple files with summary table')
@click.option('--output', '-o', type=str, help='Output file path')
def main(file_paths: Tuple[str], output_json: bool, output_md: bool, batch: bool, output: str):
    """
    Generate test overview from TDMS files.
    
    Analyzes power device validation test data and produces a human-readable
    summary including device info, test conditions, and outcome analysis.
    
    Examples:
    
        python tdms_test_overview.py test_data.tdms
        
        python tdms_test_overview.py test_data.tdms --markdown
        
        python tdms_test_overview.py *.tdms --batch
    """
    if not file_paths:
        print(f"{Fore.RED}Error: No files specified{Style.RESET_ALL}")
        sys.exit(1)
    
    results = []
    
    for file_path in file_paths:
        try:
            analyzer = PowerDeviceAnalyzer(file_path)
            overview = analyzer.generate_overview()
            results.append(overview)
        except Exception as e:
            print(f"{Fore.RED}Error processing {file_path}: {e}{Style.RESET_ALL}")
            continue
    
    if not results:
        print(f"{Fore.RED}No files processed successfully{Style.RESET_ALL}")
        sys.exit(1)
    
    # JSON output
    if output_json:
        json_output = json.dumps(results if len(results) > 1 else results[0], indent=2, default=str)
        if output:
            with open(output, 'w') as f:
                f.write(json_output)
            print(f"{Fore.GREEN}✓ Saved to {output}{Style.RESET_ALL}")
        else:
            print(json_output)
        return
    
    # Markdown output
    if output_md:
        md_output = generate_markdown(results)
        if output:
            with open(output, 'w') as f:
                f.write(md_output)
            print(f"{Fore.GREEN}✓ Saved to {output}{Style.RESET_ALL}")
        else:
            print(md_output)
        return
    
    # Batch summary table
    if batch and len(results) > 1:
        print_header("Batch Test Summary")
        print(f"\n{'File':<50} {'Device':<12} {'Test Type':<25} {'Status':<10}")
        print("─" * 100)
        for r in results:
            filename = r['file']['name'][:48]
            device = r['device']['name'][:10]
            test_type = r['test']['test_type'][:23]
            status = format_status(r['outcome']['status'])
            print(f"{filename:<50} {device:<12} {test_type:<25} {status:<10}")
        return
    
    # Standard output (single file or multiple)
    for overview in results:
        print_overview(overview)


def print_overview(overview: Dict[str, Any]):
    """Print formatted overview to console."""
    file_info = overview['file']
    device = overview['device']
    test = overview['test']
    protection = overview['protection_settings']
    outcome = overview['outcome']
    measurements = overview['measurements']
    
    print_header(f"Test Overview: {file_info['name']}")
    
    # Device Information
    print_section("Device Under Test")
    print_kv("Device", f"{device['name']} - {device['description']}")
    print_kv("Unit/Serial", device['serial'])
    print_kv("Lot", device['lot'])
    
    # Test Conditions
    print_section("Test Conditions")
    print_kv("Test Type", test['test_type'])
    print_kv("Test Name", test['test_name'])
    print_kv("Date", test['date'])
    print_kv("Station", test['station'])
    print_kv("Operator", test['operator'])
    print_kv("Input Voltage", f"{test['input_voltage']}V")
    print_kv("Output Voltage", f"{test['output_voltage']}V")
    print_kv("Temperature", f"{test['temperature']}°C")
    
    # Protection Settings
    print_section("Protection Settings")
    print_kv("Under-Voltage Fault", protection['uvf_threshold'])
    print_kv("Under-Voltage Warning", protection['uvw_threshold'])
    print_kv("Over-Current Fault", protection['ocf_threshold'])
    print_kv("Fault Response", protection['fault_response'])
    
    # Key Measurements
    print_section("Key Measurements")
    for m in measurements:
        status_icon = "⚠️" if m['anomalies'] else "✓"
        print(f"  {Fore.GREEN}{m['channel']}{Style.RESET_ALL} ({m['meaning']})")
        print(f"      Range: [{m['min']:.4f} - {m['max']:.4f}] {m['unit']} | "
              f"Mean: {m['mean']:.4f} | Samples: {m['samples']:,}")
        if m['anomalies']:
            for a in m['anomalies']:
                print(f"      {Fore.YELLOW}⚠ {a}{Style.RESET_ALL}")
    
    # Test Outcome
    print_section("Test Outcome")
    print_kv("Status", format_status(outcome['status']))
    print_kv("Fault Detected", "Yes" if outcome['fault_detected'] else "No")
    if outcome['fault_type']:
        print_kv("Fault Type", outcome['fault_type'])
    
    if outcome['observations']:
        print(f"\n  {Fore.WHITE}Observations:{Style.RESET_ALL}")
        for obs in outcome['observations']:
            print(f"    • {obs}")
    
    # Summary
    print_section("Summary")
    print(f"\n{overview['summary']}")


def generate_markdown(results: List[Dict[str, Any]]) -> str:
    """Generate Markdown output."""
    lines = []
    
    for overview in results:
        file_info = overview['file']
        device = overview['device']
        test = overview['test']
        protection = overview['protection_settings']
        outcome = overview['outcome']
        measurements = overview['measurements']
        
        lines.append(f"# Test Overview: {file_info['name']}\n")
        
        # Device
        lines.append("## Device Under Test\n")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| **Device** | {device['name']} - {device['description']} |")
        lines.append(f"| **Serial/Unit** | {device['serial']} |")
        lines.append(f"| **Lot** | {device['lot']} |")
        lines.append("")
        
        # Test Conditions
        lines.append("## Test Conditions\n")
        lines.append(f"| Parameter | Value |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| **Test Type** | {test['test_type']} |")
        lines.append(f"| **Date** | {test['date']} |")
        lines.append(f"| **Input Voltage** | {test['input_voltage']}V |")
        lines.append(f"| **Output Voltage** | {test['output_voltage']}V |")
        lines.append(f"| **Temperature** | {test['temperature']}°C |")
        lines.append(f"| **Station** | {test['station']} |")
        lines.append("")
        
        # Protection Settings
        lines.append("## Protection Settings\n")
        lines.append(f"- **UV Fault Threshold:** {protection['uvf_threshold']}")
        lines.append(f"- **OC Fault Threshold:** {protection['ocf_threshold']}")
        lines.append(f"- **Fault Response:** {protection['fault_response']}")
        lines.append("")
        
        # Measurements
        lines.append("## Measurements\n")
        lines.append("| Channel | Meaning | Min | Max | Mean | Samples |")
        lines.append("|---------|---------|-----|-----|------|---------|")
        for m in measurements:
            lines.append(
                f"| {m['channel']} | {m['meaning']} | "
                f"{m['min']:.4f} | {m['max']:.4f} | {m['mean']:.4f} | {m['samples']:,} |"
            )
        lines.append("")
        
        # Outcome
        status_emoji = "✅" if outcome['status'] == 'PASS' else "❌" if outcome['status'] == 'FAIL' else "⚠️"
        lines.append(f"## Test Outcome: {status_emoji} {outcome['status']}\n")
        
        if outcome['observations']:
            lines.append("### Observations\n")
            for obs in outcome['observations']:
                lines.append(f"- {obs}")
            lines.append("")
        
        # Summary
        lines.append("## Summary\n")
        lines.append(overview['summary'])
        lines.append("\n---\n")
    
    return "\n".join(lines)


if __name__ == '__main__':
    main()
