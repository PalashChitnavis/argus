from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.db import Base


class AnomalyResult(Base):
    """
    One row per flagged time window for a node.

    A "window" is a 5-minute bucket of aggregated telemetry (CPU, RAM, disk,
    network I/O, new processes, connections, browser visits, system/auth
    logs). Each anomaly-scan run refits an IsolationForest on the node's
    recent windows and upserts rows here for the windows it flags, keyed on
    (node_id, window_start) so re-running a scan doesn't create duplicates.

    `features` holds the raw feature vector for that window (for display).
    `contributing_features` holds the top few features by z-score deviation
    from the scan's window population, so the frontend can show *why* a
    window was flagged, not just that it was.
    """
    __tablename__ = "anomaly_results"
    __table_args__ = (
        UniqueConstraint("node_id", "window_start", name="uq_anomaly_node_window"),
    )

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)

    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_end = Column(DateTime(timezone=True), nullable=False)

    anomaly_score = Column(Float, nullable=False)  # IsolationForest decision_function; lower = more anomalous
    features = Column(JSON, nullable=False)  # {feature_name: value} raw values for this window
    contributing_features = Column(JSON, nullable=False)  # [{feature, value, z_score}, ...] top deviating features

    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    dismissed = Column(Boolean, nullable=False, default=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
