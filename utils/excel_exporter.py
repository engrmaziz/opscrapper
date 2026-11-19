"""
Excel Exporter Module for formatting extracted job leads into polished .xlsx workbooks.
Uses pandas and openpyxl with clickable hyperlinks, zebra striping, auto-fit columns, and frozen headers.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config.settings import settings
from config.logging_config import get_logger
from utils.state_manager import state_manager

logger = get_logger("ExcelExporter")


def is_valid_url(url_candidate: Any) -> bool:
    """Checks if a value is a valid HTTP/HTTPS URL string."""
    if not url_candidate or not isinstance(url_candidate, str):
        return False
    clean = url_candidate.strip().lower()
    return clean.startswith("http://") or clean.startswith("https://")


def export_to_excel(
    state_data: Optional[Union[List[Dict[str, Any]], str, Path]] = None,
    output_filename: str = "job_leads.xlsx",
) -> Path:
    """Converts extracted job leads into a formatted Excel (.xlsx) workbook.

    Args:
        state_data: List of job dictionaries, path to a JSON state file, or None (loads from StateManager).
        output_filename: Name of the output Excel file (default: 'job_leads.xlsx').

    Returns:
        Path to the saved Excel file on disk.
    """
    logger.info(f"📊 Preparing Excel export for '{output_filename}'...")

    # 1. Resolve source data
    jobs: List[Dict[str, Any]] = []

    if state_data is None:
        if state_manager.state and state_manager.state.extracted_jobs:
            jobs = list(state_manager.state.extracted_jobs)
        else:
            # Fallback to reading disk file
            if settings.STATE_FILE_PATH.exists():
                try:
                    with open(settings.STATE_FILE_PATH, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        jobs = raw.get("extracted_jobs", [])
                except Exception as e:
                    logger.warning(f"Failed to read state file from disk: {e}")
    elif isinstance(state_data, (str, Path)):
        file_path = Path(state_data)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                jobs = raw if isinstance(raw, list) else raw.get("extracted_jobs", [])
    elif isinstance(state_data, list):
        jobs = list(state_data)

    if not jobs:
        logger.warning("No job leads found to export. Generating an empty structured template.")
        jobs = [{
            "title": "No Job Leads Found",
            "company": "N/A",
            "location": "N/A",
            "source_board": "N/A",
            "board_url": "",
            "company_url": "",
            "career_page_url": "",
            "direct_apply_link": "",
            "verification_status": "empty",
            "extracted_at": datetime.utcnow().isoformat() + "Z",
        }]

    # 2. Normalize and structure DataFrame records
    records: List[Dict[str, Any]] = []
    for j in jobs:
        title = j.get("title") or j.get("job_title") or "Unknown Title"
        company = j.get("company") or j.get("company_name") or "Unknown Company"
        location = j.get("location") or "Remote"
        source_board = j.get("source_board") or j.get("board_source") or "Direct"

        board_url = j.get("board_url") or j.get("listing_url") or ""
        company_url = j.get("company_url") or ""
        career_url = j.get("career_page_url") or ""
        direct_link = j.get("direct_apply_link") or ""

        status = j.get("verification_status")
        if not status:
            if direct_link:
                status = "verified_on_company_site"
            elif career_url:
                status = "career_page_found"
            elif company_url:
                status = "domain_discovered"
            else:
                status = "board_extracted"

        extracted_at = j.get("extracted_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M")

        records.append({
            "Job Title": title,
            "Company": company,
            "Location": location,
            "Source Board": source_board,
            "Original Listing": board_url,
            "Company Website": company_url,
            "Career Page": career_url,
            "Direct Apply Link": direct_link,
            "Verification Status": status.replace("_", " ").title(),
            "Date Scraped": extracted_at[:19].replace("T", " ") if "T" in str(extracted_at) else str(extracted_at),
        })

    df = pd.DataFrame(records)

    # 3. Write and style with openpyxl
    settings.EXPORTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = settings.EXPORTS_DATA_DIR / output_filename

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Job Leads"

    # Define Theme Styles
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")  # Dark Slate
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)

    row_even_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")  # Light gray
    row_odd_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    body_font = Font(name="Segoe UI", size=10, color="0F172A")
    link_font = Font(name="Segoe UI", size=10, color="2563EB", underline="single")  # Hyperlink blue

    thin_border_side = Side(style="thin", color="E2E8F0")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # Write Header Row
    headers = list(df.columns)
    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx, col_name in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = cell_border

    # URL Column Names for Hyperlink Formatting
    url_columns = {"Original Listing", "Company Website", "Career Page", "Direct Apply Link"}

    # Write Data Rows
    for row_idx, row_data in enumerate(df.values, 2):
        ws.row_dimensions[row_idx].height = 22
        current_fill = row_even_fill if row_idx % 2 == 0 else row_odd_fill

        for col_idx, value in enumerate(row_data, 1):
            col_name = headers[col_idx - 1]
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.fill = current_fill
            cell.border = cell_border

            # Format URLs as clickable hyperlinks
            if col_name in url_columns and is_valid_url(value):
                url_str = str(value).strip()
                # Friendly display labels
                label_map = {
                    "Original Listing": "Open Listing ↗",
                    "Company Website": "Website ↗",
                    "Career Page": "Career Page ↗",
                    "Direct Apply Link": "Apply Direct ⚡",
                }
                display_label = label_map.get(col_name, "Link ↗")
                cell.value = display_label
                cell.hyperlink = url_str
                cell.font = link_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                val_str = "" if pd.isna(value) else str(value)
                cell.value = val_str
                cell.font = body_font

                if col_name in ["Location", "Source Board", "Verification Status", "Date Scraped"]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

    # 4. Freeze top header row
    ws.freeze_panes = "A2"

    # 5. Auto-fit column widths with padding
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_len = len(str(cell.value or ""))
            if val_len > max_len:
                max_len = val_len
        # Set adjusted width with min/max safety boundaries
        adjusted_width = max(max_len + 4, 14)
        ws.column_dimensions[col_letter].width = min(adjusted_width, 45)

    # Save Workbook
    wb.save(out_path)
    logger.info(f"✅ Successfully exported {len(records)} job leads to: {out_path}")
    return out_path
