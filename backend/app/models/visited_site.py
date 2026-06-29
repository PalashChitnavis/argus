from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db import Base

class VisitedSite(Base):
    """
    Browser history rows.  Two kinds share this table, distinguished by most_visited:
      most_visited=1  — per-domain aggregate (visit_count, browsers list)
      most_visited=0  — individual recent visit (url, browser)
    Rows from one collection share the same batch_id.
    Collected every 10 minutes by the agent.
    """
    __tablename__ = "visited_sites"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    # Common
    domain = Column(String, nullable=False)
    title = Column(String, nullable=True)
    last_visit_time = Column(Float, nullable=True)   # Unix timestamp

    # most_visited=1 fields
    visit_count = Column(Integer, nullable=True)
    browsers = Column(JSON, nullable=True)            # e.g. ["chrome", "firefox"]

    # most_visited=0 fields
    url = Column(String, nullable=True)
    browser = Column(String, nullable=True)

    most_visited = Column(Integer, nullable=False, default=0)  # 1 or 0
