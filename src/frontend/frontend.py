# Standard Library Imports
from typing import Tuple, Union

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.common.config import Config, logger
from src.database import AsyncDBSessionMaker
from src.frontend.components import Arena, Leaderboard


class Frontend:
    """
    Main frontend class orchestrating the Gradio UI application.

    Initializes and manages the Arena and Leaderboard components, builds the overall UI structure (Tabs, HTML),
    and handles top-level events like tab selection.
    """
    def __init__(self, config: Config, db_session_maker: AsyncDBSessionMaker):
        """
        Initializes the Frontend application controller.

        Args:
            config: The application configuration object.
            db_session_maker: An asynchronous database session factory.
        """
        self.config = config
        self.db_session_maker = db_session_maker

        # Initialize components with dependencies
        self.arena = Arena(config, db_session_maker)
        self.leaderboard = Leaderboard(db_session_maker)
        logger.debug("Frontend initialized with Arena and Leaderboard components.")

    async def handle_tab_select(self, evt: gr.SelectData) -> Tuple[
        Union[dict, gr.skip],
        Union[dict, gr.skip],
        Union[dict, gr.skip],
    ]:
        """
        Handles tab selection events. Refreshes leaderboard if its tab is selected.

        Args:
            evt: Gradio SelectData event, containing the selected tab's value (label).

        Returns:
            A tuple of Gradio update dictionaries for the leaderboard tables if the Leaderboard tab was selected
            and data needed refreshing, otherwise a tuple of gr.skip() objects.
        """
        selected_tab = evt.value
        if selected_tab == "Leaderboard":
            # Refresh leaderboard, but don't force it (allow cache/throttle)
            return await self.leaderboard.refresh_leaderboard(force=False)
        # Return skip updates for other tabs
        return gr.skip(), gr.skip(), gr.skip()

    async def build_gradio_interface(self) -> gr.Blocks:
        """
        Builds and configures the complete Gradio Blocks UI.

        Pre-loads initial leaderboard data, defines layout (HTML, Tabs), integrates Arena and Leaderboard sections,
        and sets up tab selection handler.

        Returns:
            The fully constructed Gradio Blocks application instance.
        """
        # Pre-load leaderboard data before building UI that depends on it
        await self.leaderboard.update_leaderboard_data(force=True)

        with gr.Blocks(title="Expressive TTS Arena", css_paths="static/css/styles.css") as demo:
            # --- Header HTML ---
            gr.HTML(
                value="""
                <div class="title-container">
                    <h1>Expressive TTS Arena</h1>
                    <div class="social-links">
                        <a
                            href="https://discord.com/invite/humeai"
                            target="_blank"
                            id="discord-link"
                            title="Join our Discord"
                            aria-label="Join our Discord server"
                        ></a>
                        <a
                            href="https://github.com/HumeAI/expressive-tts-arena"
                            target="_blank"
                            id="github-link"
                            title="View on GitHub"
                            aria-label="View project on GitHub"
                        ></a>
                    </div>
                </div>
                <div class="excerpt-container">
                    <p>
                        Join the community in evaluating text-to-speech models, and vote for the AI voice that best
                        captures the emotion, nuance, and expressiveness of human speech.
                    </p>
                </div>
                """
            )

            # --- Tabs ---
            with gr.Tabs() as tabs:
                with gr.TabItem("Arena"):
                    self.arena.build_arena_section()
                with gr.TabItem("Leaderboard"):
                    (
                        leaderboard_table,
                        battle_counts_table,
                        win_rates_table
                    ) = self.leaderboard.build_leaderboard_section()

            # --- Top-level Event Handlers ---
            tabs.select(
                fn=self.handle_tab_select,
                inputs=[],
                outputs=[leaderboard_table, battle_counts_table, win_rates_table],
            )

        logger.debug("Gradio interface built successfully")
        return demo
