from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Employer:
    employer_id: str
    name: str
    segment: Optional[str] = None  


@dataclass(frozen=True)
class GymLocation:
    gym_id: str
    name: str
    city: str
    state: str
    country: str = "US"


@dataclass(frozen=True)
class ProductPlan:
    product_code: str
    description: str
    billing_model: str  # "PER_VISIT", "PMPM", "HYBRID"


@dataclass(frozen=True)
class UtilizationRecord:
    

    employer_id: str
    gym_id: str
    product_code: str
    forecast_period: str  # YYYY-MM
    actual_visits: int
    eligible_members: int
    utilization_rate: float


@dataclass(frozen=True)
class PricingRule:
    

    rule_id: str
    product_code: str
    utilization_band_min: float
    utilization_band_max: float
    price_per_visit: float
    price_pmpm: float
    effective_start_date: date
    effective_end_date: Optional[date]


@dataclass(frozen=True)
class ForecastRun:
    

    run_id: str
    forecast_period: str  # YYYY-MM
    created_at: datetime
    model_version: str
    status: str  # e.g. "SUCCEEDED", "FAILED"


@dataclass(frozen=True)
class ForecastOutput:
    

    run_id: str
    employer_id: str
    gym_id: str
    product_code: str
    forecast_period: str
    forecast_visits: float


class PricingMigrationJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class PricingMigrationJob:
    

    job_id: str
    env: str
    forecast_period: str  # YYYY-MM
    tables: List[str]
    status: PricingMigrationJobStatus = PricingMigrationJobStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FileIngestionRecord:
    

    bucket: str
    key: str
    table_name: str
    logical_period: str  # forecast_period or export_date
    file_size_bytes: int
    created_at: datetime
