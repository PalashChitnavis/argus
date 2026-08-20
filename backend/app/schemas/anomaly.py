from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime


class ContributingFeature(BaseModel):
    feature: str
    value: float
    z_score: float


class AnomalyResultResponse(BaseModel):
    id: int
    node_id: int
    window_start: datetime
    window_end: datetime
    anomaly_score: float
    features: Dict[str, float]
    contributing_features: List[ContributingFeature]
    detected_at: datetime
    dismissed: bool
    dismissed_at: datetime | None = None

    class Config:
        from_attributes = True


class AnomalyScanResponse(BaseModel):
    node_id: int
    scan_range_start: datetime
    scan_range_end: datetime
    windows_scanned: int
    anomalies_found: int
    anomalies: List[AnomalyResultResponse]
    message: str | None = None  # set when there isn't enough data to run a scan
