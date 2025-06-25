import os
import re
import json
import csv
import time  # Add this import
from typing import List, Dict, Any
from tabulate import tabulate

class Output:
    # ANSI color codes
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    MARKER = u"└─ "
    TOTAL = f"{BOLD}Total:{RESET} "

    @staticmethod
    def time_taken(start_time: float) -> None:
        """Print total execution time."""
        elapsed = round((time.time() - start_time), 2)
        print(f"{Output.GREEN}\nTotal time taken: {Output.RESET}{elapsed}s")

    @staticmethod
    def sort_data(data: List[List[str]], sort_key: str) -> List[List[str]]:
        """Sort data by specified key."""
        if not data:
            return data
            
        if 'mem' in sort_key and len(data[0]) > 2:
            return sorted(data, key=lambda x: float(re.sub('[^0-9.]', '', x[2])))
        elif 'cpu' in sort_key and len(data[0]) > 1:
            return sorted(data, key=lambda x: float(re.sub('[^0-9.]', '', x[1])))
        return sorted(data, key=lambda x: x[0])

    @staticmethod
    def _calculate_percentage(used: float, total: float) -> str:
        """Calculate percentage and create bar visualization."""
        percentage = round((100 * used / total), 1) if total > 0 else 0
        bar = ''.join(['█' if i < percentage / 6 else '░' for i in range(17)])
        return f"{bar} {percentage}%"

    @staticmethod
    def bar(data: List[List[str]]) -> List[List[str]]:
        """Add percentage bars to data."""
        for line in data:
            if len(line) < 4:
                continue
                
            try:
                cpu_used = float(re.sub('[^0-9.]', '', line[1]))
                cpu_total = float(re.sub('[^0-9.]', '', line[2]))
                mem_used = float(re.sub('[^0-9.]', '', line[3]))
                mem_total = float(re.sub('[^0-9.]', '', line[4]))
                
                cpu_bar = Output._calculate_percentage(cpu_used, cpu_total)
                mem_bar = Output._calculate_percentage(mem_used, mem_total)
                
                line.insert(3, f"{Output.GREEN}{cpu_bar}{Output.RESET}")
                line.append(f"{Output.CYAN}{mem_bar}{Output.RESET}")
            except (ValueError, IndexError):
                continue
        return data

    @staticmethod
    def print_table(data: List[List[str]], headers: List[str]) -> None:
        """Print data in table format."""
        if not data:
            print("No data available")
            return
        print(tabulate(data, headers=headers, tablefmt='grid'))

    @staticmethod
    def print(data: List[List[str]], headers: List[str], format: str) -> None:
        """Print data in specified format."""
        if not data:
            return
            
        headers = [h.upper() for h in headers]
        
        if format == 'json':
            Output._print_json(data, headers)
        elif format == 'csv':
            Output._print_csv(data, headers)
        else:
            Output.print_table(data, headers)

    @staticmethod
    def _print_json(data: List[List[str]], headers: List[str]) -> None:
        """Print data in JSON format."""
        json_data = []
        for item in data:
            json_data.append(dict(zip(headers, item)))
        print(json.dumps(json_data, indent=2))

    @staticmethod
    def _print_csv(data: List[List[str]], headers: List[str]) -> None:
        """Print data in CSV format."""
        directory = './reports/csv/'
        os.makedirs(directory, exist_ok=True)
        filename = f"{directory}{headers[0]}_{int(time.time())}_report.csv"
        
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)