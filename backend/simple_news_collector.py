"""
Simple news collector for testing and development.
Standalone script that can run independently.
Connects to the main database via `database.py`.
"""

import feedparser
from datetime import datetime
from typing import List, Dict

# Import the shared database instance
from database import db

# Simple configuration - expanded feed list
FEEDS = [
    # Korean Tech News
    {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
    {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보"},
    {"feed_url": "https://rss.etnews.com/Section901.xml", "source": "전자신문_오늘의뉴스"},
    {"feed_url": "https://zdnet.co.kr/news/news_xml.asp", "source": "ZDNet Korea"},
    {"feed_url": "https://www.itworld.co.kr/rss/all.xml", "source": "ITWorld Korea"},
    {"feed_url": "https://www.bloter.net/feed", "source": "Bloter"},
    {"feed_url": "https://byline.network/feed/", "source": "Byline Network"},
    {"feed_url": "https://platum.kr/feed", "source": "Platum"},
    {"feed_url": "https://www.boannews.com/media/news_rss.xml", "source": "보안뉴스"},
    {"feed_url": "https://it.chosun.com/rss.xml", "source": "IT조선"},
    
    # Global Tech News
    {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
    {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
    {"feed_url": "https://www.engadget.com/rss.xml", "source": "Engadget"},
    {"feed_url": "https://www.wired.com/feed/rss", "source": "WIRED"},
    {"feed_url": "https://www.technologyreview.com/feed/", "source": "MIT Tech Review"},
    {"feed_url": "https://arstechnica.com/feed/", "source": "Ars Technica"},
    {"feed_url": "https://feeds.feedburner.com/venturebeat/SZYF", "source": "VentureBeat"},
    {"feed_url": "https://thenextweb.com/feed", "source": "The Next Web"},
    {"feed_url": "https://www.zdnet.com/news/rss.xml", "source": "ZDNet"},
    {"feed_url": "https://www.cnet.com/rss/news/", "source": "CNET News"},
]

def collect_from_feed(feed_url: str, source: str, max_items: int = 10) -> List[Dict]:
    """Collect news from a single RSS feed"""
    try:
        print(f"📡 Collecting from {source}...")
        feed = feedparser.parse(feed_url)
        if not hasattr(feed, 'entries') or not feed.entries:
            print(f"❌ No entries found for {source}")
            return []
        
        articles = []
        for entry in feed.entries[:max_items]:
            try:
                article = {
                    'title': getattr(entry, 'title', '').strip(),
                    'link': getattr(entry, 'link', '').strip(),
                    'published': getattr(entry, 'published', datetime.now().strftime('%Y-%m-%d')),
                    'source': source,
                    'summary': getattr(entry, 'summary', '')[:500] if hasattr(entry, 'summary') else '',
                    'keywords': [],  # Add empty keywords for compatibility
                    'raw_text': '',
                    'main_category': '기타',
                    'sub_category': '기타',
                    'language': 'ko' if '.co.kr' in feed_url or '.kr' in feed_url else 'en'
                }
                if article['title'] and article['link']:
                    articles.append(article)
            except Exception as e:
                print(f"⚠️ Error processing entry from {source}: {e}")
                continue
        
        print(f"✅ Collected {len(articles)} articles from {source}")
        return articles
        
    except Exception as e:
        print(f"❌ Error collecting from {source}: {e}")
        return []

def save_articles_to_db(articles: List[Dict]) -> Dict[str, int]:
    """Save articles to the main database using the shared db instance."""
    stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
    for article in articles:
        try:
            result = db.insert_or_update_article(article)
            if result == "inserted":
                stats['inserted'] += 1
            elif result == "updated":
                stats['updated'] += 1
        except Exception as e:
            print(f"⚠️ Error saving article '{article.get('title', '')}': {e}")
            stats['skipped'] += 1
    return stats

def run_simple_collection():
    """Run simple news collection and save to the main database."""
    print("🚀 Starting simple news collection...")
    
    # Initialize the main database (ensures tables exist)
    db.init_database()
    
    # Collect from all feeds
    all_articles = []
    for feed in FEEDS:
        articles = collect_from_feed(feed['feed_url'], feed['source'])
        all_articles.extend(articles)
    
    if not all_articles:
        print("❌ No articles collected")
        return
    
    # Save articles to the database
    stats = save_articles_to_db(all_articles)
    
    print(f"📊 Collection complete:")
    print(f"   - Total collected: {len(all_articles)}")
    print(f"   - Newly inserted: {stats['inserted']}")
    print(f"   - Updated: {stats['updated']}")
    print(f"   - Skipped (errors): {stats['skipped']}")
    
    # Show database stats from the main DB
    try:
        total_query = "SELECT COUNT(*) as count FROM articles"
        source_query = "SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC"
        
        total = db.execute_query(total_query)[0]['count']
        by_source = db.execute_query(source_query)
        
        print(f"📈 Database stats:")
        print(f"   - Total articles in DB: {total}")
        for item in by_source:
            print(f"   - {item['source']}: {item['count']}")
    except Exception as e:
        print(f"⚠️ Could not retrieve DB stats: {e}")

def get_recent_articles_from_db(limit: int = 10) -> List[Dict]:
    """Get recent articles from the main database."""
    print("\n📰 Fetching recent articles from DB...")
    try:
        return db.get_articles_with_filters(limit=limit, offset=0)
    except Exception as e:
        print(f"⚠️ Could not fetch recent articles: {e}")
        return []

if __name__ == "__main__":
    run_simple_collection()
    
    recent = get_recent_articles_from_db(5)
    if recent:
        print("\n📰 Recent articles in DB:")
        for i, article in enumerate(recent, 1):
            print(f"{i}. [{article['source']}] {article['title'][:60]}...")
