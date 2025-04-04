# Standard Library Imports
from typing import List

# Third-Party Library Imports
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.common_types import LeaderboardEntry, LeaderboardTableEntries, VotingResults

# Local Application Imports
from src.common.config import logger
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

    This function calculates voting statistics for TTS providers, using only the relevant
    comparison types for each provider, and returns data structured for a leaderboard display.

    Args:
        db (AsyncSession): The SQLAlchemy async database session.

    Returns:
        LeaderboardTableEntries: A list of LeaderboardEntry objects containing rank,
                                provider name, model name, win rate, and total votes.
    """
    default_leaderboard = [
        LeaderboardEntry("1", "", "", "0%", "0"),
        LeaderboardEntry("2", "", "", "0%", "0"),
        LeaderboardEntry("3", "", "", "0%", "0"),
    ]

    try:
        query = text(
            """
            WITH all_providers AS (
                SELECT provider FROM (VALUES ('Hume AI'), ('ElevenLabs'), ('OpenAI')) AS p(provider)
            ),
            provider_stats AS (
                SELECT
                    'Hume AI' as provider,
                    COUNT(*) as total_comparisons,
                    SUM(CASE WHEN winning_provider = 'Hume AI' THEN 1 ELSE 0 END) as wins
                FROM vote_results
                WHERE comparison_type IN ('Hume AI - ElevenLabs', 'Hume AI - OpenAI')

                UNION ALL

                SELECT
                    'ElevenLabs' as provider,
                    COUNT(*) as total_comparisons,
                    SUM(CASE WHEN winning_provider = 'ElevenLabs' THEN 1 ELSE 0 END) as wins
                FROM vote_results
                WHERE comparison_type IN ('Hume AI - ElevenLabs', 'OpenAI - ElevenLabs')

                UNION ALL

                SELECT
                    'OpenAI' as provider,
                    COUNT(*) as total_comparisons,
                    SUM(CASE WHEN winning_provider = 'OpenAI' THEN 1 ELSE 0 END) as wins
                FROM vote_results
                WHERE comparison_type IN ('Hume AI - OpenAI', 'OpenAI - ElevenLabs')
            )
            SELECT
                p.provider,
                CASE
                    WHEN p.provider = 'Hume AI' THEN 'Octave'
                    WHEN p.provider = 'ElevenLabs' THEN 'Voice Design'
                    WHEN p.provider = 'OpenAI' THEN 'gpt-4o-mini-tts'
                END as model,
                CASE
                    WHEN COALESCE(ps.total_comparisons, 0) > 0
                    THEN ROUND((COALESCE(ps.wins, 0) * 100.0 / COALESCE(ps.total_comparisons, 1))::numeric, 2)
                    ELSE 0
                END as win_rate,
                COALESCE(ps.wins, 0) as total_votes
            FROM all_providers p
            LEFT JOIN provider_stats ps ON p.provider = ps.provider
            ORDER BY win_rate DESC, total_votes DESC;
            """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        # If no rows, return default
        if not rows:
            return default_leaderboard

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

        return leaderboard_data

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching leaderboard stats: {e}")
        return default_leaderboard
    except Exception as e:
        logger.error(f"Unexpected error while fetching leaderboard stats: {e}")
        return default_leaderboard


async def get_head_to_head_battle_stats(db: AsyncSession) -> List[List[str]]:
    """
    Fetches the total number of voting results for each comparison type (excluding "Hume AI - Hume AI").

    Args:
        db (AsyncSession): The SQLAlchemy async database session.

    Returns:
        List[List[str]]: A list of lists, where each inner list contains the comparison type and the count.
    """
    default_counts = [
        ["Hume AI - OpenAI", "0"],
        ["Hume AI - ElevenLabs", "0"],
        ["OpenAI - ElevenLabs", "0"],
    ]

    try:
        query = text(
            """
            SELECT
                comparison_type,
                COUNT(*) as total
            FROM vote_results
            WHERE comparison_type != 'Hume AI - Hume AI'
            GROUP BY comparison_type
            ORDER BY comparison_type;
            """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        # If no rows, return default
        if not rows:
            return default_counts

        # Format the results
        formatted_results = []
        for row in rows:
            comparison_type, count = row
            formatted_results.append([comparison_type, str(count)])

        # Make sure all expected comparison types are included
        expected_types = {"Hume AI - OpenAI", "Hume AI - ElevenLabs", "OpenAI - ElevenLabs"}
        found_types = {row[0] for row in formatted_results}

        # Add missing types with zero counts
        for type_name in expected_types - found_types:
            formatted_results.append([type_name, "0"])

        # Sort the results by comparison type
        formatted_results.sort(key=lambda x: x[0])

        return formatted_results

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching comparison counts: {e}")
        return default_counts
    except Exception as e:
        logger.error(f"Unexpected error while fetching comparison counts: {e}")
        return default_counts


async def get_head_to_head_win_rate_stats(db: AsyncSession) -> List[List[str]]:
    """
    Calculates the win rate for each provider against the other in head-to-head comparisons.

    Args:
        db (AsyncSession): The SQLAlchemy async database session.

    Returns:
        List[List[str]]: A list of lists, where each inner list contains:
            - The comparison type
            - The win rate of the first provider (the one named first in the comparison type)
            - The win rate of the second provider (the one named second in the comparison type)
    """
    default_win_rates = [
        ["Hume AI - OpenAI", "0%", "0%"],
        ["Hume AI - ElevenLabs", "0%", "0%"],
        ["OpenAI - ElevenLabs", "0%", "0%"],
    ]

    try:
        query = text(
            """
            SELECT
                comparison_type,
                CASE WHEN COUNT(*) > 0
                    THEN ROUND(SUM(CASE
                        WHEN comparison_type = 'Hume AI - OpenAI' AND winning_provider = 'Hume AI' THEN 1
                        WHEN comparison_type = 'Hume AI - ElevenLabs' AND winning_provider = 'Hume AI' THEN 1
                        WHEN comparison_type = 'OpenAI - ElevenLabs' AND winning_provider = 'OpenAI' THEN 1
                        ELSE 0
                    END) * 100.0 / COUNT(*), 2)
                    ELSE 0
                END as first_provider_win_rate,
                CASE WHEN COUNT(*) > 0
                    THEN ROUND(SUM(CASE
                        WHEN comparison_type = 'Hume AI - OpenAI' AND winning_provider = 'OpenAI' THEN 1
                        WHEN comparison_type = 'Hume AI - ElevenLabs' AND winning_provider = 'ElevenLabs' THEN 1
                        WHEN comparison_type = 'OpenAI - ElevenLabs' AND winning_provider = 'ElevenLabs' THEN 1
                        ELSE 0
                    END) * 100.0 / COUNT(*), 2)
                    ELSE 0
                END as second_provider_win_rate
            FROM vote_results
            WHERE comparison_type != 'Hume AI - Hume AI'
            GROUP BY comparison_type
            ORDER BY comparison_type;
            """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        # If no rows, return default
        if not rows:
            return default_win_rates

        # Format the results
        formatted_results = []
        for row in rows:
            comparison_type, first_provider_win_rate, second_provider_win_rate = row
            formatted_results.append([
                comparison_type,
                f"{first_provider_win_rate}%",
                f"{second_provider_win_rate}%"
            ])

        # Make sure all expected comparison types are included
        expected_types = {"Hume AI - OpenAI", "Hume AI - ElevenLabs", "OpenAI - ElevenLabs"}
        found_types = {row[0] for row in formatted_results}

        # Add missing types with zero win rates
        for type_name in expected_types - found_types:
            formatted_results.append([type_name, "0%", "0%"])

        # Sort the results by comparison type
        formatted_results.sort(key=lambda x: x[0])

        return formatted_results

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching provider win rates: {e}")
        return default_win_rates
    except Exception as e:
        logger.error(f"Unexpected error while fetching provider win rates: {e}")
        return default_win_rates
