# Standard Library Imports
import hashlib
import json
import time
from typing import List, Optional, Tuple, Union

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.common.config import logger
from src.common.utils import get_leaderboard_data
from src.database import AsyncDBSessionMaker


class Leaderboard:
    """
    Manages the state, data fetching, and UI construction for the Leaderboard tab.

    Includes caching and throttling for leaderboard data updates.
    """
    def __init__(self, db_session_maker: AsyncDBSessionMaker):
        """
        Initializes the Leaderboard component.

        Args:
            db_session_maker: An asynchronous database session factory.
        """
        self.db_session_maker: AsyncDBSessionMaker = db_session_maker

        # leaderboard update state
        self.leaderboard_data: List[List[str]] = [[]]
        self.battle_counts_data: List[List[str]] = [[]]
        self.win_rates_data: List[List[str]] = [[]]
        self.leaderboard_cache_hash: Optional[str] = None
        self.last_leaderboard_update_time: float = 0.0
        self.min_refresh_interval: int = 30

    async def update_leaderboard_data(self, force: bool = False) -> bool:
        """
        Fetches leaderboard data from the source if cache is stale or force=True.

        Updates internal state variables (leaderboard_data, battle_counts_data,
        win_rates_data, cache_hash, last_update_time) if new data is fetched.
        Uses time-based throttling defined by `min_refresh_interval`.

        Args:
            force: If True, bypasses cache hash check and time throttling.

        Returns:
            True if the leaderboard data state was updated, False otherwise.
        """
        current_time = time.time()
        time_since_last_update = current_time - self.last_leaderboard_update_time

        # Skip update if throttled and not forced
        if not force and time_since_last_update < self.min_refresh_interval:
            logger.debug(f"Skipping leaderboard update (throttled): last updated {time_since_last_update:.1f}s ago.")
            return False

        try:
            # Fetch the latest data
            (
                latest_leaderboard_data,
                latest_battle_counts_data,
                latest_win_rates_data
            ) = await get_leaderboard_data(self.db_session_maker)

            # Check if data is valid before proceeding
            if not isinstance(latest_leaderboard_data, list) or \
               not isinstance(latest_battle_counts_data, list) or \
               not isinstance(latest_win_rates_data, list):
                logger.error("Invalid data received from get_leaderboard_data.")
                return False


            # Generate a hash of the primary leaderboard data to check for changes
            # Use a stable serialization format (sort_keys=True)
            data_str = json.dumps(latest_leaderboard_data, sort_keys=True)
            new_data_hash = hashlib.md5(data_str.encode()).hexdigest()

            # Skip if data hasn't changed and not forced
            if not force and new_data_hash == self.leaderboard_cache_hash:
                logger.debug("Leaderboard data unchanged since last fetch.")
                return False

            # Update the state and cache
            self.leaderboard_data = latest_leaderboard_data
            self.battle_counts_data = latest_battle_counts_data
            self.win_rates_data = latest_win_rates_data
            self.leaderboard_cache_hash = new_data_hash
            self.last_leaderboard_update_time = current_time
            logger.info("Leaderboard data updated successfully.")
            return True

        except Exception as e:
             logger.error(f"Failed to update leaderboard data: {e!s}", exc_info=True)
             return False

    async def refresh_leaderboard(
        self, force: bool = False
    ) -> Tuple[Union[dict, gr.skip], Union[dict, gr.skip], Union[dict, gr.skip]]:
        """
        Refreshes leaderboard data state and returns Gradio updates for the tables.

        Calls `update_leaderboard_data` and returns updates only if data changed
        or `force` is True. Returns gr.skip() otherwise.

        Args:
            force: If True, forces `update_leaderboard_data` to bypass throttling/cache.

        Returns:
            A tuple of Gradio update dictionaries for the leaderboard, battle counts,
            and win rates tables, or gr.skip() for each if no update is needed.

        Raises:
            gr.Error: If leaderboard data is empty/invalid after attempting an update.
                      (Changed from previous: now raises only if data is *still* bad)
        """
        data_updated = await self.update_leaderboard_data(force=force)

        if not self.leaderboard_data or not isinstance(self.leaderboard_data[0], list):
            logger.error("Leaderboard data is empty or invalid after update attempt.")
            raise gr.Error("Unable to retrieve leaderboard data. Please refresh the page or try again shortly.")

        if data_updated or force:
            logger.debug("Returning leaderboard table updates.")
            return (
                gr.update(value=self.leaderboard_data),
                gr.update(value=self.battle_counts_data),
                gr.update(value=self.win_rates_data)
            )
        logger.debug("Skipping leaderboard table updates (no data change).")
        return gr.skip(), gr.skip(), gr.skip()

    def build_leaderboard_section(self) -> Tuple[gr.DataFrame, gr.DataFrame, gr.DataFrame]:
        """
        Constructs the Gradio UI layout for the Leaderboard tab.

        Defines the DataFrames, HTML descriptions, and refresh button logic.

        Returns:
            A tuple containing the Gradio DataFrame components for:
            - Main Leaderboard table
            - Battle Counts table
            - Win Rates table
            These components are needed by the main Frontend class to wire up events.
        """
        logger.debug("Building Leaderboard UI section...")

        # --- UI components ---
        with gr.Row():
            with gr.Column(scale=5):
                gr.HTML(
                    value="""
                    <h2 class="tab-header">🏆 Leaderboard</h2>
                    <p style="padding-left: 8px;">
                        This leaderboard presents community voting results for different TTS providers, showing which
                        ones users found more expressive and natural-sounding. The win rate reflects how often each
                        provider was selected as the preferred option in head-to-head comparisons. Click the refresh
                        button to see the most up-to-date voting results.
                    </p>
                    """,
                    padding=False,
                )
            refresh_button = gr.Button(
                "↻ Refresh",
                variant="primary",
                elem_classes="refresh-btn",
                scale=1,
            )

        with gr.Column(elem_id="leaderboard-table-container"):
            leaderboard_table = gr.DataFrame(
                headers=["Rank", "Provider", "Model", "Win Rate", "Votes"],
                datatype=["html", "html", "html", "html", "html"],
                column_widths=[80, 300, 180, 120, 116],
                value=self.leaderboard_data,
                min_width=680,
                interactive=False,
                render=True,
                elem_id="leaderboard-table"
            )

        with gr.Column():
            gr.HTML(
                value="""
                <h2 style="padding-top: 12px;" class="tab-header">📊 Head-to-Head Matchups</h2>
                <p style="padding-left: 8px; width: 80%;">
                    These tables show how each provider performs against others in direct comparisons.
                    The first table shows the total number of comparisons between each pair of providers.
                    The second table shows the win rate (percentage) of the row provider against the column provider.
                </p>
                """,
                padding=False
            )

        with gr.Row(equal_height=True):
            with gr.Column(min_width=420):
                battle_counts_table = gr.DataFrame(
                    headers=["", "Hume AI", "OpenAI", "ElevenLabs"],
                    datatype=["html", "html", "html", "html"],
                    column_widths=[132, 132, 132, 132],
                    value=self.battle_counts_data,
                    interactive=False,
                )
            with gr.Column(min_width=420):
                win_rates_table = gr.DataFrame(
                    headers=["", "Hume AI", "OpenAI", "ElevenLabs"],
                    datatype=["html", "html", "html", "html"],
                    column_widths=[132, 132, 132, 132],
                    value=self.win_rates_data,
                    interactive=False,
                )

        with gr.Accordion(label="Citation", open=False):
            with gr.Column(variant="panel"):
                with gr.Column(variant="panel"):
                    gr.HTML(
                        value="""
                        <h2>Citation</h2>
                        <p style="padding: 0 8px;">
                            When referencing this leaderboard or its dataset in academic publications, please cite:
                        </p>
                        """,
                        padding=False,
                    )
                    gr.Markdown(
                        value="""
                        **BibTeX**
                        ```BibTeX
                        @misc{expressive-tts-arena,
                            title = {Expressive TTS Arena: An Open Platform for Evaluating Text-to-Speech Expressiveness by Human Preference},
                            author = {Alan Cowen, Zachary Greathouse, Richard Marmorstein, Jeremy Hadfield},
                            year = {2025},
                            publisher = {Hugging Face},
                            howpublished = {\\url{https://huggingface.co/spaces/HumeAI/expressive-tts-arena}}
                        }
                        ```
                        """
                    )
                    gr.HTML(
                        value="""
                        <h2>Terms of Use</h2>
                        <p style="padding: 0 8px;">
                            Users are required to agree to the following terms before using the service:
                        </p>
                        <p style="padding: 0 8px;">
                            All generated audio clips are provided for research and evaluation purposes only.
                            The audio content may not be redistributed or used for commercial purposes without
                            explicit permission. Users should not upload any private or personally identifiable
                            information. Please report any bugs, issues, or concerns to our
                            <a href="https://discord.com/invite/humeai" target="_blank" class="provider-link">
                                Discord community
                            </a>.
                        </p>
                        """,
                        padding=False,
                    )
                    gr.HTML(
                        value="""
                        <h2>Acknowledgements</h2>
                        <p style="padding: 0 8px;">
                            We thank all participants who contributed their votes to help build this leaderboard.
                        </p>
                        """,
                        padding=False,
                    )

        # Wrapper for the async refresh function
        async def async_refresh_handler() -> Tuple[Union[dict, gr.skip], Union[dict, gr.skip], Union[dict, gr.skip]]:
            """Async helper to call refresh_leaderboard and handle its tuple return."""
            logger.debug("Refresh button clicked, calling async_refresh_handler.")
            return await self.refresh_leaderboard(force=True)

        # Handler to re-enable the button after a short delay
        def reenable_button() -> dict: # Returns a Gradio update dict
            """Waits briefly and returns an update to re-enable the refresh button."""
            throttle_delay = 3 # seconds
            time.sleep(throttle_delay) # Okay in Gradio event handlers (runs in thread)
            return gr.update(interactive=True)

        # Refresh button click event handler
        refresh_button.click(
            fn=lambda _=None: (gr.update(interactive=False)), # Disable button immediately
            inputs=[],
            outputs=[refresh_button],
        ).then(
            fn=async_refresh_handler,
            inputs=[],
            outputs=[leaderboard_table, battle_counts_table, win_rates_table]  # Update all three tables
        ).then(
            fn=reenable_button, # Re-enable the button after a delay
            inputs=[],
            outputs=[refresh_button]
        )

        logger.debug("Leaderboard UI section built.")
        # Return the component instances needed by the Frontend class
        return leaderboard_table, battle_counts_table, win_rates_table
