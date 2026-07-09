"""Canonical record schema. Every state scraper normalizes into this."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Project:
    state: str                       # e.g. "Maharashtra"
    rera_reg_no: str                 # registration number (unique key with state)
    project_name: str
    status: str = ""                 # Registered / Upcoming / Applied / Lapsed / Revoked
    promoter_name: str = ""
    promoter_address: str = ""
    promoter_contact: str = ""
    project_type: str = ""           # Residential / Commercial / Plotted / Mixed
    district: str = ""
    locality: str = ""
    address: str = ""
    pincode: str = ""
    approved_on: str = ""
    proposed_completion: str = ""
    total_units: str = ""
    total_area_sqm: str = ""
    detail_url: str = ""
    source_url: str = ""
    scraped_at: str = ""
    extra: dict = field(default_factory=dict)  # portal-specific fields, kept as JSON

    def to_row(self) -> dict:
        d = asdict(self)
        import json
        d["extra"] = json.dumps(d["extra"], ensure_ascii=False)
        return d
