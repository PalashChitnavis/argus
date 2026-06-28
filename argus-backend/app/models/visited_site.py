from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db import Base

class VisitedSite(Base):
    """
    One row per domain per five-minute snapshot.

    browser_history entries (most_visited=True):
      domain       — e.g. "youtube.com"
      visit_count  — all-time total visits across all browsers
      last_visit_time — Unix timestamp of most recent visit
      browsers     — JSON list of browser names that recorded this domain
      title        — sample page title for this domain
      most_visited — True

    recently_visited entries (most_visited=False):
      url          — full URL of individual visit
      domain       — extracted domain
      title        — page title at time of visit
      last_visit_time — Unix timestamp of this specific visit
      browser      — which browser recorded it
      most_visited — False
    """
    __tablename__ = "visited_sites"

    id                  = Column(Integer, primary_key=True, index=True)
    five_minute_data_id = Column(Integer, ForeignKey("five_minute_data.id"), nullable=False, index=True)

    # Common fields
    domain          = Column(String, nullable=False)
    title           = Column(String, nullable=True)
    last_visit_time = Column(Float, nullable=True)   # Unix timestamp

    # browser_history fields (most_visited=True)
    visit_count = Column(Integer, nullable=True)
    browsers    = Column(JSON, nullable=True)         # e.g. ["chrome", "firefox"]

    # recently_visited fields (most_visited=False)
    url     = Column(String, nullable=True)
    browser = Column(String, nullable=True)

    # Distinguishes the two lists so the read endpoint can separate them
    most_visited = Column(Integer, nullable=False, default=0)  # 1=most_visited, 0=recently_visited

    five_minute_data = relationship("FiveMinuteData", back_populates="visited_sites")