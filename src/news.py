from gnews import GNews
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def format_news_time(published_at: str) -> str:
    """
    Formats a news article's published time into a human-readable relative time string.

    Args:
        published_at (str): The published timestamp in ISO 8601 format (e.g., '2024-02-19T10:30:00+00:00').

    Returns:
        str: A formatted time string (e.g., "Just now", "5 minutes ago", "2 hours ago", or "2024-02-19 10:30").
    """
    published_time = datetime.strptime(published_at, '%a, %d %b %Y %H:%M:%S GMT')
    published_time = published_time.replace(tzinfo=ZoneInfo('EST'))
    time_diff = datetime.now(published_time.tzinfo) - published_time

    if time_diff < timedelta(minutes=1):
        return "Just now"
    elif time_diff < timedelta(hours=1):
        return f"{int(time_diff.total_seconds() // 60)} minutes ago"
    elif time_diff < timedelta(days=1):
        return f"{int(time_diff.total_seconds() // 3600)} hours ago"
    else:
        return published_time.strftime('%Y-%m-%d %H:%M')

def get_news_update(symbol: str, query=None, period='1d', num_articles=5):
    """
    Fetches the latest news articles for a given stock symbol.

    Args:
        symbol (str): The stock symbol to fetch news for.
        num_articles (int): The number of news articles to retrieve.
    """
    g_news = GNews(
        language='en',
        period=period,
        max_results=num_articles
    )
    news = g_news.get_news(query + symbol + ' stock')

    return news

def single_format(news) -> str:
    """
    Returns a simple formatted string across all news articles.
    
    :param news: A dict of news article(s).
        Keys: 'title', 'description', 'url', 'publisher', 'published_at'
    :return: A formatted string of news articles.
    :rtype: str
    """
    formatted_news = []
    for article in news:

        time_str = format_news_time(article['published_at'])
        
        formatted_news.append(f"{article['title']}\n{article['description']}\nPublished by {article['publisher']} - {time_str}\nRead more: {article['url']}\n")

        return "\n\n".join(formatted_news)

def embed_format(news) -> dict:
    """
    Returns a formatted embed dict for Discord.

    :param news: A list of news article dictionaries.
    :return: A dictionary representing a Discord embed.
    :rtype: dict
    """
    embed_news = []
    for article in news:
        time_str = format_news_time(article['published date'])
        embed_news.append({
            'title': article['title'],
            'description': f"{article['description']} - {time_str}\n[Read more]({article['url']})",
            'author': article['publisher'],
            'timestamp': time_str
        })

    return embed_news