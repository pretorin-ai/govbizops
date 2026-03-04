"""
Database engine, session, and SQLAlchemy model for opportunity storage.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Text, create_engine, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Opportunity(Base):
    __tablename__ = "opportunities"

    notice_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solicitation_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opp_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posted_date: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_deadline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    naics_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    psc_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ui_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    office_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type_of_set_aside: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type_of_contract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    point_of_contact: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    collected_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    scraped_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to the dict format expected by downstream consumers."""
        return {
            "noticeId": self.notice_id,
            "title": self.title,
            "solicitationNumber": self.solicitation_number,
            "type": self.opp_type,
            "postedDate": self.posted_date,
            "responseDeadLine": self.response_deadline,
            "naicsCode": self.naics_code,
            "pscCode": self.psc_code,
            "uiLink": self.ui_link,
            "description": self.description,
            "organizationName": self.organization_name,
            "officeAddress": self.office_address,
            "pointOfContact": self.point_of_contact,
            "typeOfSetAside": self.type_of_set_aside,
            "typeOfContract": self.type_of_contract,
        }

    @classmethod
    def from_api_response(cls, opp: Dict[str, Any]) -> "Opportunity":
        """Create an Opportunity from a SAM.gov API response dict."""
        return cls(
            notice_id=opp["noticeId"],
            title=opp.get("title"),
            solicitation_number=opp.get("solicitationNumber"),
            opp_type=opp.get("type"),
            posted_date=opp.get("postedDate"),
            response_deadline=opp.get("responseDeadLine"),
            naics_code=opp.get("naicsCode"),
            psc_code=opp.get("pscCode"),
            ui_link=opp.get("uiLink"),
            description=opp.get("description"),
            organization_name=opp.get("organizationName"),
            office_address=opp.get("officeAddress"),
            type_of_set_aside=opp.get("typeOfSetAside"),
            type_of_contract=opp.get("typeOfContract"),
            point_of_contact=opp.get("pointOfContact"),
            raw_data=opp,
        )


def get_engine(database_url: Optional[str] = None):
    """Create a SQLAlchemy engine from the given URL or DATABASE_URL env var."""
    url = database_url or os.environ.get("DATABASE_URL", "sqlite:///govbizops.db")
    return create_engine(url)


def get_session(engine) -> sessionmaker[Session]:
    """Return a session factory bound to the given engine."""
    return sessionmaker(bind=engine)


def init_db(engine) -> None:
    """Create all tables."""
    Base.metadata.create_all(engine)
