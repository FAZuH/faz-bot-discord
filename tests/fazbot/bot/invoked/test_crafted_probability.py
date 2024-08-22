import unittest
from unittest.mock import MagicMock, patch

from fazbot.bot.invoke.invoke_crafted_probability import InvokeCraftedProbability


class TestCraftedProbability(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.image_asset = MagicMock()
        InvokeCraftedProbability._View = MagicMock
        InvokeCraftedProbability.ASSET_CRAFTINGTABLE = self.image_asset
        return super().setUp()

    async def test_run(self) -> None:
        interaction = MagicMock()
        ing_strs = ["1,2,50", "1,2,50", "1,2,50", "1,2,50"]
        with patch("fazbot.bot.bot.Bot", autospec=True) as mock_bot:
            self.mock_bot = mock_bot
        craftedprob = InvokeCraftedProbability(self.mock_bot, interaction, ing_strs)
        for ing in craftedprob._craftutil.ingredients:
            self.assertEqual(ing.min_value, 1)
            self.assertEqual(ing.max_value, 2)
            self.assertEqual(ing.boost, 50)
