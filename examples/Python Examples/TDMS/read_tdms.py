#!/usr/bin/env python3
"""
TDMS File Reader Example

This script demonstrates how to read and analyze TDMS (Technical Data Management Streaming) 
files using the nptdms library. TDMS is a binary file format developed by National Instruments
commonly used for storing measurement and test data.

Features:
- List all groups and channels in a TDMS file
- Display file, group, and channel properties
- Extract and analyze channel data
- Export data to CSV format
- Generate basic statistics

Requirements:
    pip install nptdms numpy pandas click colorama

Usage:
    python read_tdms.py <file_path>                    # Show file summary
    python read_tdms.py <file_path> --groups           # List all groups
    python read_tdms.py <file_path> --channels         # List all channels
    python read_tdms.py <file_path> --properties       # Show all properties
    python read_tdms.py <file_path> --stats            # Show data statistics
    python read_tdms.py <file_path> --export output.csv  # Export to CSV
    python read_tdms.py <file_path> --group "HDO8k"    # Show specific group details
    python read_tdms.py <file_path> --channel "HDO8k/VOUT"  # Show specific channel data

Author: Generated for SystemLink Enterprise Examples
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import click
    from colorama import init, Fore, Style
    import numpy as np
    from nptdms import TdmsFile
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install nptdms numpy click colorama")
    sys.exit(1)

# Initialize colorama for cross-platform colored output
init()


class TdmsReader:
    """A class for reading and analyzing TDMS files."""
    
    def __init__(self, file_path: str):
        """
        Initialize the TDMS reader with a file path.
        
        Args:
            file_path: Path to the TDMS file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"TDMS file not found: {file_path}")
        
        self.tdms_file = TdmsFile.read(str(self.file_path))
    
    def get_file_properties(self) -> Dict[str, Any]:
        """Get all file-level properties."""
        return dict(self.tdms_file.properties)
    
    def get_groups(self) -> List[str]:
        """Get list of group names."""
        return [group.name for group in self.tdms_file.groups()]
    
    def get_group_properties(self, group_name: str) -> Dict[str, Any]:
        """Get properties for a specific group."""
        group = self.tdms_file[group_name]
        return dict(group.properties)
    
    def get_channels(self, group_name: Optional[str] = None) -> List[str]:
        """
        Get list of channel names.
        
        Args:
            group_name: Optional group name to filter channels. 
                       If None, returns all channels in format "group/channel"
        """
        channels = []
        if group_name:
            group = self.tdms_file[group_name]
            channels = [ch.name for ch in group.channels()]
        else:
            for group in self.tdms_file.groups():
                for channel in group.channels():
                    channels.append(f"{group.name}/{channel.name}")
        return channels
    
    def get_channel_info(self, group_name: str, channel_name: str) -> Dict[str, Any]:
        """Get detailed information about a channel."""
        channel = self.tdms_file[group_name][channel_name]
        
        info = {
            'name': channel.name,
            'group': group_name,
            'path': channel.path,
            'data_type': str(channel.dtype) if hasattr(channel, 'dtype') else 'unknown',
            'length': len(channel),
            'properties': dict(channel.properties),
        }
        
        # Add data statistics if numeric
        if len(channel) > 0:
            try:
                data = channel[:]
                if np.issubdtype(data.dtype, np.number):
                    info['statistics'] = {
                        'min': float(np.min(data)),
                        'max': float(np.max(data)),
                        'mean': float(np.mean(data)),
                        'std': float(np.std(data)),
                    }
            except Exception:
                pass
        
        return info
    
    def get_channel_data(self, group_name: str, channel_name: str, 
                         start: int = 0, count: Optional[int] = None) -> np.ndarray:
        """
        Get channel data as a numpy array.
        
        Args:
            group_name: Name of the group
            channel_name: Name of the channel
            start: Starting index
            count: Number of samples to return (None for all)
        """
        channel = self.tdms_file[group_name][channel_name]
        data = channel[:]
        
        if count is not None:
            return data[start:start + count]
        return data[start:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the TDMS file."""
        summary = {
            'file_name': self.file_path.name,
            'file_size_mb': self.file_path.stat().st_size / (1024 * 1024),
            'file_properties': self.get_file_properties(),
            'groups': [],
            'total_channels': 0,
            'total_data_points': 0,
        }
        
        for group in self.tdms_file.groups():
            group_info = {
                'name': group.name,
                'properties': dict(group.properties),
                'channels': [],
            }
            
            for channel in group.channels():
                channel_len = len(channel)
                channel_info = {
                    'name': channel.name,
                    'length': channel_len,
                    'dtype': str(channel.dtype) if hasattr(channel, 'dtype') else 'unknown',
                }
                group_info['channels'].append(channel_info)
                summary['total_channels'] += 1
                summary['total_data_points'] += channel_len
            
            summary['groups'].append(group_info)
        
        return summary
    
    def export_to_csv(self, output_path: str, group_name: Optional[str] = None):
        """
        Export TDMS data to CSV format.
        
        Args:
            output_path: Path for the output CSV file
            group_name: Optional group to export (None exports all)
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for CSV export: pip install pandas")
        
        groups_to_export = [group_name] if group_name else self.get_groups()
        
        for grp_name in groups_to_export:
            group = self.tdms_file[grp_name]
            data = {}
            
            for channel in group.channels():
                data[channel.name] = channel[:]
            
            if data:
                df = pd.DataFrame(data)
                
                # Generate output filename
                if len(groups_to_export) > 1:
                    base, ext = os.path.splitext(output_path)
                    file_path = f"{base}_{grp_name}{ext}"
                else:
                    file_path = output_path
                
                df.to_csv(file_path, index=False)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Exported {grp_name} to {file_path}")


def format_value(value: Any) -> str:
    """Format a value for display."""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Fore.YELLOW}{title}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'-' * 40}{Style.RESET_ALL}")


@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--groups', is_flag=True, help='List all groups')
@click.option('--channels', is_flag=True, help='List all channels')
@click.option('--properties', is_flag=True, help='Show all properties')
@click.option('--stats', is_flag=True, help='Show data statistics for all channels')
@click.option('--export', type=str, help='Export data to CSV file')
@click.option('--group', type=str, help='Show details for a specific group')
@click.option('--channel', type=str, help='Show details for a specific channel (format: group/channel)')
@click.option('--samples', type=int, default=10, help='Number of sample values to show (default: 10)')
def main(file_path: str, groups: bool, channels: bool, properties: bool, 
         stats: bool, export: str, group: str, channel: str, samples: int):
    """
    Read and analyze TDMS files.
    
    FILE_PATH: Path to the TDMS file to read.
    
    Examples:
    
        python read_tdms.py data.tdms
        
        python read_tdms.py data.tdms --groups
        
        python read_tdms.py data.tdms --channel "HDO8k/VOUT" --samples 20
        
        python read_tdms.py data.tdms --export output.csv
    """
    try:
        reader = TdmsReader(file_path)
        
        # Show specific channel details
        if channel:
            if '/' not in channel:
                print(f"{Fore.RED}Error: Channel must be in format 'group/channel'{Style.RESET_ALL}")
                sys.exit(1)
            
            group_name, channel_name = channel.split('/', 1)
            print_header(f"Channel: {channel}")
            
            info = reader.get_channel_info(group_name, channel_name)
            
            print(f"  Path: {info['path']}")
            print(f"  Data Type: {info['data_type']}")
            print(f"  Length: {info['length']:,} samples")
            
            if info.get('properties'):
                print_section("Properties")
                for key, value in info['properties'].items():
                    print(f"  {key}: {format_value(value)}")
            
            if info.get('statistics'):
                print_section("Statistics")
                for key, value in info['statistics'].items():
                    print(f"  {key}: {format_value(value)}")
            
            # Show sample data
            data = reader.get_channel_data(group_name, channel_name, count=samples)
            print_section(f"First {len(data)} Samples")
            for i, val in enumerate(data):
                print(f"  [{i}] {format_value(val)}")
            
            return
        
        # Show specific group details
        if group:
            print_header(f"Group: {group}")
            
            props = reader.get_group_properties(group)
            if props:
                print_section("Properties")
                for key, value in props.items():
                    print(f"  {key}: {format_value(value)}")
            
            print_section("Channels")
            for ch_name in reader.get_channels(group):
                ch_info = reader.get_channel_info(group, ch_name)
                print(f"  {Fore.GREEN}{ch_name}{Style.RESET_ALL}")
                print(f"    Length: {ch_info['length']:,} | Type: {ch_info['data_type']}")
                if ch_info.get('statistics'):
                    s = ch_info['statistics']
                    print(f"    Range: [{format_value(s['min'])} - {format_value(s['max'])}] | Mean: {format_value(s['mean'])}")
            
            return
        
        # Export to CSV
        if export:
            print_header("Exporting to CSV")
            reader.export_to_csv(export)
            return
        
        # List groups only
        if groups:
            print_header("Groups")
            for grp in reader.get_groups():
                channels_count = len(reader.get_channels(grp))
                print(f"  {Fore.GREEN}{grp}{Style.RESET_ALL} ({channels_count} channels)")
            return
        
        # List all channels
        if channels:
            print_header("Channels")
            for ch in reader.get_channels():
                print(f"  {ch}")
            return
        
        # Show all properties
        if properties:
            print_header("All Properties")
            
            file_props = reader.get_file_properties()
            if file_props:
                print_section("File Properties")
                for key, value in file_props.items():
                    print(f"  {key}: {format_value(value)}")
            
            for grp in reader.get_groups():
                grp_props = reader.get_group_properties(grp)
                if grp_props:
                    print_section(f"Group: {grp}")
                    for key, value in grp_props.items():
                        print(f"  {key}: {format_value(value)}")
                
                for ch in reader.get_channels(grp):
                    ch_info = reader.get_channel_info(grp, ch)
                    if ch_info.get('properties'):
                        print(f"\n  {Fore.CYAN}Channel: {ch}{Style.RESET_ALL}")
                        for key, value in ch_info['properties'].items():
                            print(f"    {key}: {format_value(value)}")
            return
        
        # Show statistics
        if stats:
            print_header("Channel Statistics")
            for grp in reader.get_groups():
                print_section(f"Group: {grp}")
                for ch in reader.get_channels(grp):
                    ch_info = reader.get_channel_info(grp, ch)
                    print(f"\n  {Fore.GREEN}{ch}{Style.RESET_ALL}")
                    print(f"    Samples: {ch_info['length']:,}")
                    if ch_info.get('statistics'):
                        s = ch_info['statistics']
                        print(f"    Min: {format_value(s['min'])}")
                        print(f"    Max: {format_value(s['max'])}")
                        print(f"    Mean: {format_value(s['mean'])}")
                        print(f"    Std Dev: {format_value(s['std'])}")
            return
        
        # Default: Show file summary
        summary = reader.get_summary()
        
        print_header(f"TDMS File: {summary['file_name']}")
        print(f"  Size: {summary['file_size_mb']:.2f} MB")
        print(f"  Groups: {len(summary['groups'])}")
        print(f"  Total Channels: {summary['total_channels']}")
        print(f"  Total Data Points: {summary['total_data_points']:,}")
        
        # File properties
        if summary['file_properties']:
            print_section("File Properties")
            for key, value in summary['file_properties'].items():
                print(f"  {key}: {format_value(value)}")
        
        # Groups and channels
        print_section("Groups and Channels")
        for grp in summary['groups']:
            print(f"\n  {Fore.GREEN}📁 {grp['name']}{Style.RESET_ALL}")
            if grp['properties']:
                for key, value in list(grp['properties'].items())[:3]:
                    print(f"     {Fore.BLUE}{key}:{Style.RESET_ALL} {format_value(value)}")
            
            for ch in grp['channels']:
                print(f"     └─ {ch['name']} ({ch['length']:,} pts, {ch['dtype']})")
        
        print(f"\n{Fore.CYAN}Tip: Use --help to see all available options{Style.RESET_ALL}")
        
    except FileNotFoundError as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error reading TDMS file: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == '__main__':
    main()
