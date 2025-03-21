"""
crud.py

This module defines the operations for the Expressive TTS Arena project's database.
Since vote records are never updated or deleted, only functions to create and read votes are provided.
"""

# Third-Party Library Imports
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# Local Application Imports
from src.config import logger
from src.custom_types import LeaderboardEntry, LeaderboardTableEntries, VotingResults
from src.database.models import VoteResult


async def create_vote(db: AsyncSession, vote_data: VotingResults) -> VoteResult:
    """
    Create a new vote record in the database based on the given VotingResults data.

    Args:
        db (AsyncSession): The SQLAlchemy async database session.
        vote_data (VotingResults): The vote data to persist.

    Returns:
        VoteResult: The newly created vote record.
    """
    try:

        # Create vote record
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
            await db.commit()
            await db.refresh(vote)
            logger.info(f"Vote record created successfully: ID={vote.id}")
            return vote
        except SQLAlchemyError as db_error:
            await db.rollback()
            logger.error(f"Database error while creating vote: {db_error}")
            raise
    except ValueError as val_error:
        logger.error(f"Invalid vote data: {val_error}")
        raise
    except Exception as e:
        if db:
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback operation: {rollback_error}")

        logger.error(f"Unexpected error creating vote record: {e}")
        raise


async def get_leaderboard_stats(db: AsyncSession) -> LeaderboardTableEntries:
    """
    Fetches voting statistics from the database to populate a leaderboard.

    This function calculates voting statistics for TTS providers, excluding Hume-to-Hume
    comparisons, and returns data structured for a leaderboard display.

    Args:
        db (AsyncSession): The SQLAlchemy async database session.

    Returns:
        LeaderboardTableEntries: A list of LeaderboardEntry objects containing rank,
                                provider name, model name, win rate, and total votes.
    """
    default_leaderboard = [
        LeaderboardEntry("1", "", "", "0%", "0"),
        LeaderboardEntry("2", "", "", "0%", "0")
    ]

    try:
        query = text(
            """
            WITH provider_stats AS (
                -- Get wins for Hume AI
                SELECT
                    'Hume AI' as provider,
                    COUNT(*) as total_comparisons,
                    SUM(CASE WHEN winning_provider = 'Hume AI' THEN 1 ELSE 0 END) as wins
                FROM vote_results
                WHERE comparison_type != 'Hume AI - Hume AI'

                UNION ALL

                -- Get wins for ElevenLabs
                SELECT
                    'ElevenLabs' as provider,
                    COUNT(*) as total_comparisons,
                    SUM(CASE WHEN winning_provider = 'ElevenLabs' THEN 1 ELSE 0 END) as wins
                FROM vote_results
                WHERE comparison_type != 'Hume AI - Hume AI'
            )
            SELECT
                provider,
                CASE
                    WHEN provider = 'Hume AI' THEN 'Octave'
                    WHEN provider = 'ElevenLabs' THEN 'Voice Design'
                END as model,
                CASE
                    WHEN total_comparisons > 0 THEN ROUND((wins * 100.0 / total_comparisons)::numeric, 2)
                    ELSE 0
                END as win_rate,
                wins as total_votes
            FROM provider_stats
            ORDER BY win_rate DESC;
            """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        # Format the data for the leaderboard
        leaderboard_data = []
        for i, row in enumerate(rows, 1):
            provider, model, win_rate, total_votes = row
            leaderboard_entry = LeaderboardEntry(
                rank=f"{i}",
                provider=provider,
                model=model,
                win_rate=f"{win_rate}%",
                votes=f"{total_votes}"
            )
            leaderboard_data.append(leaderboard_entry)

        # If no data was found, return default entries
        if not leaderboard_data:
            return default_leaderboard

        return leaderboard_data

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching leaderboard stats: {e}")
        return default_leaderboard
    except Exception as e:
        logger.error(f"Unexpected error while fetching leaderboard stats: {e}")
        return default_leaderboard
