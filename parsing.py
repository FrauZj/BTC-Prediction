from newsapi import NewsApiClient
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import sys
import os
import json

OUTPUT_FOLDER = "data"
JSON_FILENAME = "news.json"
NEWS_API_KEY = "d7f7f2f45ad14d1cbaa6f68952f8a8e1"  # Replace if needed
KEYWORDS = "bitcoin OR crypto OR ethereum OR solana OR nft"
LANGUAGE = 'en'

def get_date_range(time_str):
    now = datetime.now()
    time_str = time_str.strip().lower()

    if time_str.endswith('d'):
        days = int(time_str.replace('d', ''))
        from_date = now - timedelta(days=days)
    elif time_str.endswith('w'):
        weeks = int(time_str.replace('w', ''))
        from_date = now - timedelta(weeks=weeks)
    elif time_str.endswith('m'):
        months = int(time_str.replace('m', ''))
        from_date = now - relativedelta(months=months)
    else:
        from_date = now - timedelta(weeks=1)

    if (now - from_date).days > 30:
        from_date = now - timedelta(days=30)

    return from_date.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')

def fetch_crypto_news(from_date, to_date):
    if NEWS_API_KEY == "ВСТАВТЕ_ВАШ_NEWS_API_KEY_СЮДИ" or not NEWS_API_KEY:
        print("[News] API Key missing.")
        return []

    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        all_articles = newsapi.get_everything(
            q=KEYWORDS,
            language=LANGUAGE,
            from_param=from_date,
            to=to_date,
            sort_by='relevancy',
            page_size=100
        )

        if all_articles['status'] == 'ok':
            return all_articles['articles']
        else:
            print(f"[News] API Error: {all_articles.get('message', 'Unknown')}")
            return []

    except Exception as e:
        print(f"[News] Connection/API Error: {e}")
        return []

def save_to_json(articles, time_period):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    file_path = os.path.join(OUTPUT_FOLDER, JSON_FILENAME)

    if not articles:
        # Create an empty valid JSON
        empty_data = {
            "metadata": {"total_articles": 0},
            "articles": []
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, indent=4)
        return False

    news_data = {
        "metadata": {
            "report_title": "CRYPTO NEWS",
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "requested_period": time_period,
            "source": "NewsAPI.org",
            "total_articles": len(articles)
        },
        "articles": []
    }

    for article in articles:
        article_data = {
            "newsletter_name": article['source'].get('name', 'N/A'),
            "data": article.get('publishedAt', 'N/A'),
            "headline": article.get('title', 'N/A'),
            "description": article.get('description', ''),
            "link": article.get('url', 'N/A')
        }
        news_data["articles"].append(article_data)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=4)
        print(f"[News] Saved {len(articles)} articles to {file_path}")
        return True
    except Exception as e:
        print(f"[News] Save Error: {e}")
        return False

def run_news_parsing(period="1w"):
    start_date, end_date = get_date_range(period)
    print(f"[News] Fetching news from {start_date} to {end_date}...")
    articles = fetch_crypto_news(start_date, end_date)
    return save_to_json(articles, period)

if __name__ == "__main__":
    user_input = input("Enter time period (e.g., 1d, 7d, 1m): ")
    run_news_parsing(user_input)