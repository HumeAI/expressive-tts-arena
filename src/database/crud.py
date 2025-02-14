"""
crud.py

This module defines the operations for the Expressive TTS Arena project's database.
Since vote records are never updated or deleted, only functions to create and read votes are provided.
"""

# Third-Party Library Imports
from sqlalchemy.orm import Session

# Local Application Imports
from src.custom_types import VotingResults
from src.database.models import VoteResult


def create_vote(db: Session, vote_data: VotingResults) -> VoteResult:
    """
    Create a new vote record in the database based on the given VotingResults data.

    Args:
        db (Session): The SQLAlchemy database session.
        vote_data (VotingResults): The vote data to persist.

    Returns:
        VoteResult: The newly created vote record.
    """
    vote = VoteResult(
        comparison_type=vote_data["comparison_type"],
        winning_provider=vote_data["winning_provider"],
        winning_option=vote_data["winning_option"],
        option_a_provider=vote_data["option_a_provider"],
        option_b_provider=vote_data["option_b_provider"],
        option_a_generation_id=vote_data["option_a_generation_id"],
        option_b_generation_id=vote_data["option_b_generation_id"],
        voice_description=vote_data["character_description"],
        text=vote_data["text"],
        is_custom_text=vote_data["is_custom_text"],
    )
    db.add(vote)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    db.refresh(vote)
    return vote
