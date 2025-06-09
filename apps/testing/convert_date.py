from unittest import TestCase
from utils.scraper import convert_date

class TestConverDate(TestCase):
    #Pengujian Fungsi convert date
    def test_convert_date_success(self):
        assert convert_date("05/25/2023, 02:30 PM, +0000 UTC") == "2023-05-25"

    def test_convert_date_failure(sefl):
        assert convert_date("24/20/2022") == "0000-00-00"

