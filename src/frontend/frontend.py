# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.common.config import Config, logger
from src.database import AsyncDBSessionMaker
from src.frontend.components import Arena, Leaderboard


class Frontend:
    """
    Main frontend class that coordinates all UI components and manages application state.

    This class brings together the Arena and Leaderboard components and serves
    as the primary entry point for the Gradio UI.
    """
    def __init__(self, config: Config, db_session_maker: AsyncDBSessionMaker):
        self.config = config
        self.db_session_maker = db_session_maker

        self.arena = Arena(config, db_session_maker)
        self.leaderboard = Leaderboard(db_session_maker)

    async def handle_tab_select(self, evt: gr.SelectData):
        """
        Handles tab selection events and refreshes the leaderboard if the Leaderboard tab is selected.

        Args:
            evt (gr.SelectData): Event data containing information about the selected tab

        Returns:
            tuple: Updates for the three tables if data changed, otherwise skip
        """
        if evt.value == "Leaderboard":
            return await self.leaderboard.refresh_leaderboard(force=False)
        return gr.skip(), gr.skip(), gr.skip()

    async def build_gradio_interface(self) -> gr.Blocks:
        """
        Builds and configures the fully constructed Gradio UI layout.
        """
        with gr.Blocks(title="Expressive TTS Arena", css_paths="static/css/styles.css") as demo:
            await self.leaderboard.update_leaderboard_data()
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

            with gr.Tabs() as tabs:
                with gr.TabItem("Arena"):
                    self.arena.build_arena_section()
                with gr.TabItem("Leaderboard"):
                    (
                        leaderboard_table,
                        battle_counts_table,
                        win_rates_table
                    ) = self.leaderboard.build_leaderboard_section()

            tabs.select(
                fn=self.handle_tab_select,
                inputs=[],
                outputs=[leaderboard_table, battle_counts_table, win_rates_table],
            )

        logger.debug("Gradio interface built successfully")
        return demo
