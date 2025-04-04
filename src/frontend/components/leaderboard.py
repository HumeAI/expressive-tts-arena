# Standard Library Imports
import hashlib
import json
import time
from typing import List, Optional, Tuple

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.common.config import logger
from src.common.utils import get_leaderboard_data
from src.database import AsyncDBSessionMaker


class Leaderboard:
    def __init__(self, db_session_maker: AsyncDBSessionMaker):
        self.db_session_maker = db_session_maker

        # leaderboard update state
        self.leaderboard_data: List[List[str]] = [[]]
        self.battle_counts_data: List[List[str]] = [[]]
        self.win_rates_data: List[List[str]] = [[]]
        self.leaderboard_cache_hash: Optional[str] = None
        self.last_leaderboard_update_time: float = 0.0
        self.min_refresh_interval = 30

    async def update_leaderboard_data(self, force: bool = False) -> bool:
        """
        Fetches the latest leaderboard data only if needed based on cache and time constraints.

        Args:
            force (bool): If True, bypass the time-based throttling.

        Returns:
            bool: True if the leaderboard was updated, False otherwise.
        """
        current_time = time.time()
        time_since_last_update = current_time - self.last_leaderboard_update_time

        # Skip update if it's been less than min_refresh_interval seconds and not forced
        if not force and time_since_last_update < self.min_refresh_interval:
            logger.debug(f"Skipping leaderboard update: last updated {time_since_last_update:.1f}s ago.")
            return False

        # Fetch the latest data
        (
            latest_leaderboard_data,
            latest_battle_counts_data,
            latest_win_rates_data
        ) = await get_leaderboard_data(self.db_session_maker)

        # Generate a hash of the new data to check if it's changed
        data_str = json.dumps(str(latest_leaderboard_data))
        data_hash = hashlib.md5(data_str.encode()).hexdigest()

        # Check if the data has changed
        if data_hash == self.leaderboard_cache_hash and not force:
            logger.debug("Leaderboard data unchanged since last fetch.")
            return False

        # Update the cache and timestamp
        self.leaderboard_data = latest_leaderboard_data
        self.battle_counts_data = latest_battle_counts_data
        self.win_rates_data = latest_win_rates_data
        self.leaderboard_cache_hash = data_hash
        self.last_leaderboard_update_time = current_time
        logger.debug("Leaderboard data updated successfully.")
        return True

    async def refresh_leaderboard(self, force: bool = False) -> Tuple[gr.DataFrame, gr.DataFrame, gr.DataFrame]:
        """
        Asynchronously fetches and formats the latest leaderboard data.

        Args:
            force (bool): If True, bypass time-based throttling.

        Returns:
            tuple: Updated DataFrames or gr.skip() if no update needed
        """
        data_updated = await self.update_leaderboard_data(force=force)

        if not self.leaderboard_data:
            raise gr.Error("Unable to retrieve leaderboard data. Please refresh the page or try again shortly.")

        if data_updated or force:
            return (
                gr.update(value=self.leaderboard_data),
                gr.update(value=self.battle_counts_data),
                gr.update(value=self.win_rates_data)
            )
        return gr.skip(), gr.skip(), gr.skip()

    def build_leaderboard_section(self) -> gr.DataFrame:
        """
        Builds the Leaderboard section
        """
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
        async def async_refresh_handler():
            leaderboard_update, battle_counts_update, win_rates_update = await self.refresh_leaderboard(force=True)
            return leaderboard_update, battle_counts_update, win_rates_update

        # Handler to re-enable the button after a refresh
        def reenable_button() -> gr.Button:
            time.sleep(3) # wait 3 seconds before enabling to prevent excessive data fetching
            return gr.update(interactive=True)

        # Refresh button click event handler
        refresh_button.click(
            fn=lambda _=None: (gr.update(interactive=False)),
            inputs=[],
            outputs=[refresh_button],
        ).then(
            fn=async_refresh_handler,
            inputs=[],
            outputs=[leaderboard_table, battle_counts_table, win_rates_table]  # Update all three tables
        ).then(
            fn=reenable_button,
            inputs=[],
            outputs=[refresh_button]
        )

        return leaderboard_table, battle_counts_table, win_rates_table
