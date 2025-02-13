"""
models.py

This module defines the SQLAlchemy ORM models for the Expressive TTS Arena project.
It currently defines the VoteResult model representing the vote_results table.
"""

# Standard Library Imports
from enum import Enum

# Third-Party Library Imports
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as saEnum,
)
from sqlalchemy import (
    text as sa_text,
)

# Local Application Imports
from src.database.database import Base


class OptionEnum(str, Enum):
    OPTION_A = "option_a"
    OPTION_B = "option_b"


class VoteResult(Base):
    __tablename__ = "vote_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    comparison_type = Column(String(50), nullable=False)
    winning_provider = Column(String(50), nullable=False)
    winning_option = Column(saEnum(OptionEnum), nullable=False)
    option_a_provider = Column(String(50), nullable=False)
    option_b_provider = Column(String(50), nullable=False)
    option_a_generation_id = Column(String(100), nullable=True)
    option_b_generation_id = Column(String(100), nullable=True)
    voice_description = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    is_custom_text = Column(Boolean, nullable=False, server_default=sa_text("false"))

    __table_args__ = (
        Index("idx_created_at", "created_at"),
        Index("idx_comparison_type", "comparison_type"),
        Index("idx_winning_provider", "winning_provider"),
    )

    def __repr__(self):
        return (
            f"<VoteResult(id={self.id}, created_at={self.created_at}, "
            f"comparison_type={self.comparison_type}, winning_provider={self.winning_provider})>"
        )
