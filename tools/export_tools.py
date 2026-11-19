"""
Excel export tools for Antigravity Agent using pandas and openpyxl.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from config.settings import settings
from .base import BaseAgentTool, registry
from utils.excel_exporter import export_to_excel


class ExcelExportTool(BaseAgentTool):
    """Exports and styles verified job leads into a formatted Excel workbook (.xlsx)."""

    name = "export_jobs_to_excel"
    description = (
        "Exports verified job leads, company websites, career portals, and direct application links "
        "into a formatted Excel workbook (.xlsx) with clickable hyperlinks, frozen headers, and auto-fit columns."
    )

    async def execute(
        self,
        job_listings: Optional[List[Dict[str, Any]]] = None,
        output_filename: str = "job_leads.xlsx",
    ) -> Dict[str, Any]:
        """Executes Excel export."""
        export_path = export_to_excel(state_data=job_listings, output_filename=output_filename)
        return {
            "status": "success",
            "export_path": str(export_path),
            "file_size_bytes": export_path.stat().st_size if export_path.exists() else 0,
        }


# Register tool instance into global registry
registry.register(ExcelExportTool())
