import requests
import json
import datetime
import pandas as pd
from datetime import datetime, timedelta
import os
import numpy as np
import re
import time
import math


class TimeSeriesPredictor:
    def __init__(self, json_file_path="data/btc_prices.json", news_file_path=None):
        self.news_context = []
        self.price_history = []
        self.json_file_path = json_file_path
        self.news_file_path = news_file_path
        self.time_gap_hours = None

        self.load_price_data()
        if news_file_path:
            self.load_news_data()
        self.calculate_time_gap()

    def load_price_data(self):
        if not os.path.exists(self.json_file_path):
            raise FileNotFoundError(f"Price data file not found: {self.json_file_path}")

        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.price_history = data
        except Exception as e:
            print(f"Error loading price data: {e}")
            self.price_history = []

    def load_news_data(self):
        if not self.news_file_path or not os.path.exists(self.news_file_path):
            return

        try:
            with open(self.news_file_path, 'r', encoding='utf-8') as f:
                news_data = json.load(f)

            articles = news_data.get('articles', [])
            for article in articles:
                headline = article.get('headline', '')
                description = article.get('description', '')
                news_text = f"{headline}. {description}"
                timestamp = article.get('data', '').replace('T', ' ').replace('Z', '')

                if news_text.strip() and timestamp:
                    self.news_context.append({
                        "time": timestamp,
                        "news": news_text
                    })
            # Keep only recent news
            self.news_context = self.news_context[-10:]

        except Exception as e:
            print(f"Error loading news data: {e}")

    def calculate_time_gap(self):
        if len(self.price_history) < 2:
            self.time_gap_hours = 24
            return

        try:
            time_diffs = []
            for i in range(1, min(10, len(self.price_history))):
                time1 = datetime.strptime(self.price_history[i - 1]['time'], '%Y-%m-%d %H:%M:%S')
                time2 = datetime.strptime(self.price_history[i]['time'], '%Y-%m-%d %H:%M:%S')
                diff_hours = (time2 - time1).total_seconds() / 3600
                time_diffs.append(diff_hours)

            self.time_gap_hours = np.median(time_diffs)
            if self.time_gap_hours == 0:
                self.time_gap_hours = 1  # Prevent division by zero

        except Exception as e:
            print(f"Error calculating time gap: {e}")
            self.time_gap_hours = 24

    def create_initial_prediction_prompt(self, num_predictions=100):
        reference_price = self.price_history[-1]['price'] if self.price_history else 0

        news_context_formatted = ""
        if self.news_context:
            news_context_formatted = "RECENT CONTEXT:\n"
            for i, item in enumerate(self.news_context):
                news_context_formatted += f"{i + 1}. [{item['time']}] {item['news']}\n"

        prompt = f"""You are a financial AI. Predict exactly {num_predictions} future Bitcoin prices based on the trend.

        DATA:
        Last 10 prices: {json.dumps(self.price_history[-10:], indent=2)}
        Current Price: {reference_price}
        Interval: approx {self.time_gap_hours} hours

        {news_context_formatted}

        RULES:
        1. Return ONLY a JSON array of {num_predictions} numbers. e.g. [50100.5, 50200.1, ...]
        2. No text, no explanations.
        3. Prices must be positive.
        """
        return prompt

    def make_prediction_request(self, prompt, timeout=45):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama2",  # Ensure you have this model or change it
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1000
                    }
                },
                timeout=timeout
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", ""), True
            else:
                return f"HTTP {response.status_code}", False

        except requests.exceptions.ConnectionError:
            return "Connection refused. Is Ollama running?", False
        except Exception as e:
            return f"Request error: {str(e)}", False

    def parse_prediction(self, response_text, expected_count):
        try:
            # Attempt 1: JSON extraction
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            if start != -1 and end != 0:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                if isinstance(data, list):
                    # Filter non-numbers
                    clean_data = [float(x) for x in data if
                                  isinstance(x, (int, float, str)) and str(x).replace('.', '', 1).isdigit()]
                    if clean_data:
                        return clean_data
        except:
            pass
        numbers = re.findall(r'\b\d+\.\d+\b|\b\d+\b', response_text)
        if len(numbers) >= expected_count * 0.5:  # at least half expected
            return [float(n) for n in numbers]

        return None

    def predict(self, num_predictions=100):
        print(f"Requesting {num_predictions} predictions from AI...")

        prompt = self.create_initial_prediction_prompt(num_predictions)
        response_text, success = self.make_prediction_request(prompt)

        if not success:
            raise Exception(f"AI Request Failed: {response_text}")

        predictions = self.parse_prediction(response_text, num_predictions)

        if not predictions:
            raise Exception("AI returned invalid format (could not parse numbers).")

        # Ensure we return exactly num_predictions if we got more
        if len(predictions) > num_predictions:
            predictions = predictions[:num_predictions]

        # If we got significantly fewer, treat as failure
        if len(predictions) < num_predictions * 0.5:
            raise Exception(f"AI returned too few data points ({len(predictions)} vs {num_predictions} requested).")

        return predictions

    def generate_future_dates(self, num_predictions, timeframe):
        if not self.price_history:
            return []

        last_timestamp = datetime.strptime(self.price_history[-1]['time'], '%Y-%m-%d %H:%M:%S')

        timeframe_hours = {
            "1h": 1, "4h": 4, "1d": 24,
            "5d": 24 * 5, "1wk": 24 * 7, "1mo": 24 * 30
        }.get(timeframe, 24)

        future_dates = []
        for i in range(1, num_predictions + 1):
            future_date = last_timestamp + timedelta(hours=timeframe_hours * i)
            future_dates.append(future_date.strftime('%Y-%m-%d %H:%M:%S'))

        return future_dates