import unittest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.davos')

from retail_ops.sub_agents.product_trend_mapper import ProductTrendMapper

class TestCoucheTardLogic(unittest.TestCase):
    def setUp(self):
        self.mapper = ProductTrendMapper()

    def test_coffee_opportunity(self):
        # Cold weather should trigger Coffee opportunity
        opportunity = self.mapper.get_consumption_gap_by_weather(temperature=5, time_of_day="08:00")
        self.assertEqual(opportunity, "Coffee")

    def test_sloche_opportunity(self):
        # Hot weather should trigger Sloche opportunity
        opportunity = self.mapper.get_consumption_gap_by_weather(temperature=30, time_of_day="14:00")
        self.assertEqual(opportunity, "Sloche")

    def test_snack_opportunity(self):
        # Moderate weather should trigger Snack opportunity
        opportunity = self.mapper.get_consumption_gap_by_weather(temperature=20, time_of_day="12:00")
        self.assertEqual(opportunity, "Snack")

if __name__ == "__main__":
    unittest.main()
