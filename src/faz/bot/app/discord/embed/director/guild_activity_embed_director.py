from __future__ import annotations

from datetime import timedelta
from typing import override, Sequence, TYPE_CHECKING

from nextcord import Embed
from sortedcontainers import SortedList
from tabulate import tabulate

from faz.bot.app.discord.embed.builder.custom_description_builder import CustomDescriptionBuilder
from faz.bot.app.discord.embed.builder.pagination_embed_builder import PaginationEmbedBuilder
from faz.bot.app.discord.embed.director._base_pagination_embed_director import (
    BasePaginationEmbedDirector,
)
from faz.bot.app.discord.view._view_utils import ViewUtils

if TYPE_CHECKING:
    from datetime import datetime

    from faz.bot.database.fazwynn.model.guild_info import GuildInfo
    from faz.bot.database.fazwynn.model.player_activity_history import PlayerActivityHistory

    from faz.bot.app.discord.view.wynn_history.guild_activity_view import GuildActivityView


class GuildActivityEmbedDirector(BasePaginationEmbedDirector):
    def __init__(
        self,
        view: GuildActivityView,
        guild: GuildInfo,
        period_begin: datetime,
        period_end: datetime,
        show_inactive: bool,
    ) -> None:
        self._period_begin = period_begin
        self._period_end = period_end
        self._guild = guild
        self._show_inactive = show_inactive

        begin_ts = int(period_begin.timestamp())
        end_ts = int(period_end.timestamp())

        self._desc_builder = CustomDescriptionBuilder().set_builder_initial_lines(
            [("Period", f"<t:{begin_ts}:R> to <t:{end_ts}:R>")]
        )
        self._embed_builder = PaginationEmbedBuilder(
            view.interaction, items_per_page=10
        ).set_builder_initial_embed(Embed(title=f"Guild Member Activity ({guild.name})"))

        self._db = view.bot.app.create_fazwynn_db()

    @override
    async def setup(self) -> None:
        await self._fetch_data()
        self._embed_builder.set_builder_items(self._items)

    @override
    def construct(self) -> Embed:
        builder = self.embed_builder
        page = builder.current_page
        items = builder.get_items(page)

        if len(items) == 0:
            description = "```ml\nNo data found.\n```"
        else:
            description = (
                "\n```ml\n"
                + tabulate(
                    [
                        [n, res.username, res.playtime_string]  # type: ignore
                        for n, res in enumerate(items, 1)
                    ],
                    headers=["No", "Username", "Activity"],
                    tablefmt="github",
                )
                + "\n```"
            )

        embed = self.prepare_default().set_builder_page(page).set_description(description).build()
        return embed

    async def _fetch_data(self) -> None:
        await self._guild.awaitable_attrs.members

        self._items = SortedList()
        for player in self._guild.members:
            entities = await self._db.player_activity_history.get_activities_between_period(
                player.uuid, self._period_begin, self._period_end
            )
            playtime = self._get_activity_time(entities, self._period_begin, self._period_end)
            activity_result = _ActivityResult(player.latest_username, playtime)
            if not self._show_inactive and activity_result.playtime.total_seconds() < 60:
                continue
            self._items.add(activity_result)

    @staticmethod
    def _get_activity_time(
        entities: Sequence[PlayerActivityHistory],
        period_begin: datetime,
        period_end: datetime,
    ) -> timedelta:
        res = 0
        begin_ts = period_begin.timestamp()
        end_ts = period_end.timestamp()
        for e in entities:
            on_ts = e.logon_datetime.timestamp()
            off_ts = e.logoff_datetime.timestamp()
            on = begin_ts if on_ts <= begin_ts else on_ts
            off = end_ts if off_ts >= end_ts else off_ts
            res += off - on
        ret = timedelta(seconds=res)
        return ret

    @property
    @override
    def embed_builder(self) -> PaginationEmbedBuilder:
        return self._embed_builder


class _ActivityResult:
    def __init__(self, username: str, playtime: timedelta) -> None:
        self._username = username
        self._playtime = playtime
        self._playtime_string = ViewUtils.format_timedelta(playtime)

    @property
    def username(self) -> str:
        return self._username

    @property
    def playtime(self) -> timedelta:
        return self._playtime

    @property
    def playtime_string(self) -> str:
        return self._playtime_string

    def __lt__(self, other: int) -> bool:
        if isinstance(other, _ActivityResult):
            return self.playtime < other.playtime
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _ActivityResult):
            return self.playtime == other.playtime
        return NotImplemented
