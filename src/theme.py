"""
theme.py

This module defines a custom Gradio theme.
- For more information on Gradio themes see: https://www.gradio.app/docs/gradio/themes
- For manual styling with css, see /src/assets/styles.css
"""

# Standard Library Imports
from __future__ import annotations
from collections.abc import Iterable

# Third-Party Library Imports
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes

class CustomTheme(Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.purple,  
        secondary_hue: colors.Color | str = colors.stone,  
        neutral_hue: colors.Color | str = colors.neutral,  
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont('Source Sans Pro'),
            'ui-sans-serif',
            'system-ui',
            'sans-serif',
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont('IBM Plex Mono'),
            'ui-monospace',
            'Consolas',
            'monospace',
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        self.name = 'custom_theme'
        super().set(
            # --- Colors ---
            error_background_fill='#EF4444',
            # error_background_fill_dark='',
            error_border_color='#B91C1C',
            # error_border_color_dark='',
            error_icon_color='#B91C1C',
            # error_icon_color_dark='',
            input_background_fill='#F9FAFB',
            # input_background_fill_dark='',

            # --- Shadows ---
            input_shadow_focus='0 0 0 *shadow_spread #7C3AED80, *shadow_inset',
            # input_shadow_focus_dark='',
            
            # --- Gradients ---
            stat_background_fill='linear-gradient(to right, #7C3AED, #D8B4FE)',
            # stat_background_fill_dark='',

            # --- Button borders ---
            button_border_width='0px',
            input_border_width='1px',

            # --- Primary Button ---
            button_primary_background_fill='#111111',
            # button_primary_background_fill_dark='',
            button_primary_background_fill_hover='#3F3F3F',
            # button_primary_background_fill_hover_dark='',
            button_primary_text_color='#FFFFFF',
            # button_primary_text_color_dark='',

            # --- Secondary Button ---
            button_secondary_background_fill='#E5E7EB',
            # button_secondary_background_fill_dark='#4B5563',
            button_secondary_background_fill_hover='#D1D5DB',
            # button_secondary_background_fill_hover_dark='#374151',
            button_secondary_text_color='#111827',
            # button_secondary_text_color_dark='#FFFFFF',

            # --- Cancel Button ---
            button_cancel_background_fill='#EF4444',
            # button_cancel_background_fill_dark='#B91C1C',
            button_cancel_background_fill_hover='#DC2626',
            # button_cancel_background_fill_hover_dark='#991B1B',
            button_cancel_text_color='#FFFFFF',
            # button_cancel_text_color_dark='#FFFFFF',
            button_cancel_text_color_hover='#FFFFFF',
            # button_cancel_text_color_hover_dark='#FFFFFF',

            # --- Other ---
            border_color_accent_subdued='#A78BFA',
        )