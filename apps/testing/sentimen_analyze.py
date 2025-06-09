from unittest import TestCase
from unittest.mock import patch
from utils import model

class TestAnalyzeSentiment(TestCase):
    def test_empty_text(self):
        self.assertEqual(model.analyze_sentiment(""), "Tidak Diketahui")
        self.assertEqual(model.analyze_sentiment("   "), "Tidak Diketahui")

    @patch('utils.model.svm', None)
    @patch('utils.model.vectorizer', None)
    def test_model_none(self):
        self.assertEqual(model.analyze_sentiment("Halo"), "Model tidak tersedia")

    @patch('utils.model.vectorizer')
    @patch('utils.model.svm')
    def test_prediction(self, mock_svm, mock_vectorizer):
        mock_vectorizer.transform.return_value = "vectorized_text"
        mock_svm.predict.return_value = ["Positif"]

        result = model.analyze_sentiment("Ini kalimat positif")
        self.assertEqual(result, "Positif")

