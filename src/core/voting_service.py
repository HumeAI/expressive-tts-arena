# Standard Library Imports
import json
from typing import List, Tuple

# Third-Party Library Imports
from sqlalchemy.ext.asyncio import AsyncSession

# Local Application Imports
from src.common import constants
from src.common.common_types import (
    ComparisonType,
    LeaderboardEntry,
    OptionKey,
    OptionMap,
    TTSProviderName,
    VotingResults,
)
from src.common.config import logger
from src.database import (
    AsyncDBSessionMaker,
    create_vote,
    get_head_to_head_battle_stats,
    get_head_to_head_win_rate_stats,
    get_leaderboard_stats,
)


class VotingService:
    """
    Service for handling all database interactions related to voting and leaderboards.

    Encapsulates logic for submitting votes and retrieving formatted leaderboard statistics.
    """

    def __init__(self, db_session_maker: AsyncDBSessionMaker):
        """
        Initializes the VotingService.

        Args:
            db_session_maker: An asynchronous database session factory.
        """
        self.db_session_maker: AsyncDBSessionMaker = db_session_maker
        logger.debug("VotingService initialized.")

    async def _create_db_session(self) -> AsyncSession | None:
        """
        Creates a new database session, returning None if it's a dummy session.

        Returns:
            An active AsyncSession or None if using a dummy session factory.
        """
        session = self.db_session_maker()
        # Check for a dummy session marker if your factory provides one
        is_dummy_session = getattr(session, "is_dummy", False)

        if is_dummy_session:
            logger.debug("Using dummy DB session; operations will be skipped.")
            # Ensure dummy sessions are also closed if they have resources
            if hasattr(session, "close"):
                await session.close()
            return None

        logger.debug("Created new DB session.")
        return session

    def _determine_comparison_type(self, provider_a: TTSProviderName, provider_b: TTSProviderName) -> ComparisonType:
        """
        Determine the comparison type based on the given TTS provider names.

        Args:
            provider_a (TTSProviderName): The first TTS provider.
            provider_b (TTSProviderName): The second TTS provider.

        Returns:
            ComparisonType: The determined comparison type.

        Raises:
            ValueError: If the combination of providers is not recognized.
        """
        if provider_a == constants.HUME_AI and provider_b == constants.HUME_AI:
            return constants.HUME_TO_HUME

        providers = (provider_a, provider_b)

        if constants.HUME_AI in providers and constants.ELEVENLABS in providers:
            return constants.HUME_TO_ELEVENLABS

        if constants.HUME_AI in providers and constants.OPENAI in providers:
            return constants.HUME_TO_OPENAI

        if constants.ELEVENLABS in providers and constants.OPENAI in providers:
            return constants.OPENAI_TO_ELEVENLABS

        raise ValueError(f"Invalid provider combination: {provider_a}, {provider_b}")

    async def _persist_vote(self, voting_results: VotingResults) -> None:
        """
        Persists a vote record in the database using a dedicated session.

        Handles session creation, commit, rollback, and closure. Logs errors internally.

        Args:
            voting_results: A dictionary containing the vote details.
        """
        session = await self._create_db_session()
        if session is None:
            logger.info("Skipping vote persistence (dummy session).")
            self._log_voting_results(voting_results)
            return

        try:
            self._log_voting_results(voting_results)
            await create_vote(session, voting_results)
            logger.info("Vote successfully persisted.")
        except Exception as e:
            logger.error(f"Failed to persist vote record: {e}", exc_info=True)
        finally:
            await session.close()
            logger.debug("DB session closed after persisting vote.")

    def _log_voting_results(self, voting_results: VotingResults) -> None:
        """Logs the full voting results dictionary."""
        try:
            logger.info("Voting results:\n%s", json.dumps(voting_results, indent=4, default=str))
        except TypeError:
            logger.error("Could not serialize voting results for logging.")
            logger.info(f"Voting results (raw): {voting_results}")

    def _format_leaderboard_data(self, leaderboard_data_raw: List[LeaderboardEntry]) -> List[List[str]]:
        """Formats raw leaderboard entries into HTML strings for the UI table."""
        # Ensure constants.TTS_PROVIDER_LINKS is accessible, maybe pass via __init__ if not global
        formatted_data = []
        for rank, provider, model, win_rate, votes in leaderboard_data_raw:
            provider_info = constants.TTS_PROVIDER_LINKS.get(provider, {})
            provider_link = provider_info.get("provider_link", "#")
            model_link = provider_info.get("model_link", "#")

            formatted_data.append([
                f'<p style="text-align: center;">{rank}</p>',
                f'<a href="{provider_link}" target="_blank" class="provider-link">{provider}</a>',
                f'<a href="{model_link}" target="_blank" class="provider-link">{model}</a>',
                f'<p style="text-align: center;">{win_rate}</p>',
                f'<p style="text-align: center;">{votes}</p>',
            ])
        return formatted_data


    def _format_battle_counts_data(self, battle_counts_data_raw: List[List[str]]) -> List[List[str]]:
        """Formats raw battle counts into an HTML matrix for the UI."""
        battle_counts_dict = {item[0]: str(item[1]) for item in battle_counts_data_raw}
        providers = constants.TTS_PROVIDERS

        formatted_matrix: List[List[str]] = []
        for row_provider in providers:
            row = [f'<p style="padding-left: 8px;"><strong>{row_provider}</strong></p>']
            for col_provider in providers:
                if row_provider == col_provider:
                    cell_value = "-"
                else:
                    comparison_key = self._determine_comparison_type(row_provider, col_provider)
                    cell_value = battle_counts_dict.get(comparison_key, "0")
                row.append(f'<p style="text-align: center;">{cell_value}</p>')
            formatted_matrix.append(row)
        return formatted_matrix


    def _format_win_rate_data(self, win_rate_data_raw: List[List[str]]) -> List[List[str]]:
        """Formats raw win rates into an HTML matrix for the UI."""
        # win_rate_data_raw expected as [comparison_type, first_win_rate_str, second_win_rate_str]
        win_rates = {}
        for comparison_type, first_win_rate, second_win_rate in win_rate_data_raw:
            # Comparison type should already be canonical 'ProviderA - ProviderB'
            try:
                provider1, provider2 = comparison_type.split(" - ")
                win_rates[(provider1, provider2)] = first_win_rate
                win_rates[(provider2, provider1)] = second_win_rate
            except ValueError:
                logger.warning(f"Could not parse comparison_type '{comparison_type}' in win rate data.")
                continue # Skip malformed entry

        providers = constants.TTS_PROVIDERS
        formatted_matrix: List[List[str]] = []
        for row_provider in providers:
            row = [f'<p style="padding-left: 8px;"><strong>{row_provider}</strong></p>']
            for col_provider in providers:
                cell_value = "-" if row_provider == col_provider else win_rates.get((row_provider, col_provider), "0%")
                row.append(f'<p style="text-align: center;">{cell_value}</p>')
            formatted_matrix.append(row)
        return formatted_matrix

    async def get_formatted_leaderboard_data(self) -> Tuple[
        List[List[str]],
        List[List[str]],
        List[List[str]],
    ]:
        """
        Fetches raw leaderboard stats and formats them for UI display.

        Retrieves overall rankings, battle counts, and win rates, then formats
        them into HTML strings suitable for Gradio DataFrames.

        Returns:
            A tuple containing formatted lists of lists for:
            - Leaderboard rankings table
            - Battle counts matrix
            - Win rate matrix
            Returns empty lists ([[]], [[]], [[]]) on failure.
        """
        session = await self._create_db_session()
        if session is None:
            logger.info("Skipping leaderboard fetch (dummy session).")
            return [[]], [[]], [[]]

        try:
            # Fetch raw data using underlying CRUD functions
            leaderboard_data_raw = await get_leaderboard_stats(session)
            battle_counts_data_raw = await get_head_to_head_battle_stats(session)
            win_rate_data_raw = await get_head_to_head_win_rate_stats(session)
            logger.debug("Fetched raw leaderboard data successfully.")

            # Format the data
            leaderboard_data = self._format_leaderboard_data(leaderboard_data_raw)
            battle_counts_data = self._format_battle_counts_data(battle_counts_data_raw)
            win_rate_data = self._format_win_rate_data(win_rate_data_raw)

            return leaderboard_data, battle_counts_data, win_rate_data

        except Exception as e:
            logger.error(f"Failed to fetch and format leaderboard data: {e}", exc_info=True)
            return [[]], [[]], [[]] # Return empty structure on error
        finally:
            await session.close()
            logger.debug("DB session closed after fetching leaderboard data.")

    async def submit_vote(
        self,
        option_map: OptionMap,
        selected_option: OptionKey,
        text_modified: bool,
        character_description: str,
        text: str,
    ) -> None:
        """
        Constructs and persists a vote record based on user selection and context.

        This method is designed to be called safely from background tasks, handling all internal exceptions.

        Args:
            option_map: Mapping of comparison data and TTS options.
            selected_option: The option key ('option_a' or 'option_b') selected by the user.
            text_modified: Indicates if the text was custom vs. generated.
            character_description: Description used for TTS generation.
            text: The text synthesized.
        """
        try:
            provider_a: TTSProviderName = option_map[constants.OPTION_A_KEY]["provider"]
            provider_b: TTSProviderName = option_map[constants.OPTION_B_KEY]["provider"]

            comparison_type: ComparisonType = self._determine_comparison_type(provider_a, provider_b)

            voting_results: VotingResults = {
                "comparison_type": comparison_type,
                "winning_provider": option_map[selected_option]["provider"],
                "winning_option": selected_option,
                "option_a_provider": provider_a,
                "option_b_provider": provider_b,
                "option_a_generation_id": option_map[constants.OPTION_A_KEY]["generation_id"],
                "option_b_generation_id": option_map[constants.OPTION_B_KEY]["generation_id"],
                "character_description": character_description,
                "text": text,
                "is_custom_text": text_modified,
            }

            await self._persist_vote(voting_results)

        except KeyError as e:
            logger.error(
                f"Missing key in option_map during vote submission: {e}. OptionMap: {option_map}",
                exc_info=True
            )
        except Exception as e:
            logger.error(f"Unexpected error in submit_vote: {e}", exc_info=True)
