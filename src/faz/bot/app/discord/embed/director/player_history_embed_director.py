from __future__ import annotations

from datetime import datetime
from typing import override, Self, TYPE_CHECKING
from uuid import UUID

from faz.bot.database.fazwynn.model.player_info import PlayerInfo
from nextcord import Embed
import pandas as pd

from faz.bot.app.discord.embed.builder.description_builder import DescriptionBuilder
from faz.bot.app.discord.embed.builder.field_pagination_embed_builder import (
    FieldPaginationEmbedBuilder,
)
from faz.bot.app.discord.embed.builder.player_history_field_builder import PlayerHistoryFieldBuilder
from faz.bot.app.discord.embed.director._base_pagination_embed_director import (
    BasePaginationEmbedDirector,
)
from faz.bot.app.discord.select.player_history_data_option import PlayerHistoryDataOption

if TYPE_CHECKING:
    from faz.bot.app.discord.view.wynn_history.player_history_view import PlayerHistoryView


class PlayerHistoryEmbedDirector(BasePaginationEmbedDirector):
    def __init__(
        self,
        view: PlayerHistoryView,
        player: PlayerInfo,
        period_begin: datetime,
        period_end: datetime,
        character_labels: dict[str, str],
    ) -> None:
        self._character_labels = character_labels
        self._period_begin = period_begin
        self._period_end = period_end
        self._player = player

        begin_ts = int(period_begin.timestamp())
        end_ts = int(period_end.timestamp())

        self._desc_builder = DescriptionBuilder().set_builder_initial_lines(
            [("Period", f"<t:{begin_ts}:R> to <t:{end_ts}:R>")]
        )
        self._embed_builder = FieldPaginationEmbedBuilder(
            view.interaction, items_per_page=4
        ).set_builder_initial_embed(Embed(title=f"Player History ({player.latest_username})"))
        self.field_builder = PlayerHistoryFieldBuilder().set_character_labels(character_labels)

        self._db = view.bot.app.create_fazwynn_db()

    @override
    async def setup(self) -> None:
        """Async initialization method. Must be run once."""
        await self._fetch_data()
        self.field_builder.set_data(self._player_df, self._char_df)

    def set_options(self, data: PlayerHistoryDataOption, character_uuid: str | None = None) -> Self:
        self._data = data
        self._character_uuid = character_uuid
        return self

    @override
    def construct(self) -> Embed:
        character_uuid = self._character_uuid
        data = self._data
        if character_uuid is None:
            char_df = self._char_df
            char_label = "All characters"
        else:
            char_df: pd.DataFrame = self._char_df[  # type: ignore
                self._char_df["character_uuid"] == UUID(character_uuid).bytes
            ]
            char_label = self._character_labels[character_uuid]

        fields = self.field_builder.set_data_option(data).set_character_data(char_df).build()
        desc = (
            self._desc_builder.reset()
            .add_line("Charater", char_label)
            .add_line("Data", data.value.value)
            .build()
        )
        embed = self.prepare_default().set_description(desc).set_builder_items(fields).build()

        return embed

    async def _fetch_data(self) -> None:
        await self._player.awaitable_attrs.characters

        self._char_df = pd.DataFrame()
        for ch in self._player.characters:
            df_char_ = self._db.character_history.select_between_period_as_dataframe(
                ch.character_uuid, self._period_begin, self._period_end
            )
            if df_char_.empty:
                continue
            self._char_df = pd.concat([self._char_df, df_char_])

        self._player_df = self._db.player_history.select_between_period_as_dataframe(
            self._player.uuid, self._period_begin, self._period_end
        )

    @property
    @override
    def embed_builder(self) -> FieldPaginationEmbedBuilder:
        return self._embed_builder
