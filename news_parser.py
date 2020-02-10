from bs4 import BeautifulSoup
import dateparser
import requests
import logging

import datetime

from sqlalchemy import Column, Integer, String, UniqueConstraint, Float, ForeignKey
from sqlalchemy.sql import exists

from db_base import Base, engine, Session


class NewsLink(Base):
    __tablename__ = 'news_links'

    id = Column(Integer, autoincrement=True, primary_key=True)
    link = Column(String, unique=True)
    ts = Column(Float)

    def __init__(self, link, ts):
        self.link = link
        self.ts = ts

    def __repr__(self):
        return 'Link<id={}, link={}, ts={}>' \
            .format(self.id, self.link, self.ts)

class ReadHistory(Base):
    __tablename__ = 'read_history'

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer)
    link_id = Column(Integer, ForeignKey("news_links.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'link_id', name='_history_location_'),
    )

    def __init__(self, user_id, link_id):
        self.user_id = user_id
        self.link_id = link_id

    def __repr__(self):
        return 'History<id={}, user_id={}, link_id={}>' \
            .format(self.id, self.user_id, self.link_id)


Base.metadata.create_all(engine)


class NewsRecord:
    def __init__(self, link, ts=-1):
        self.link = link
        self.ts = ts

    def set_time(self, ts):
        self.ts = ts

    def __eq__(self, other):
        self.link == other.link


class StreamingNews:
    def __init__(self, sources):
        self.news_map = {}
        self.readed_news = {}
        self.full_news_list = []
        self.sources = sources
        self.logger = logging.getLogger(self.__class__.__name__)

        self.db_session = Session()
        # self._recovery_history()

    # def _recovery_history(self):
    #     history_entries = self.db_session.query(ReadHistory).all()

    #     self.logger.info('Recovery len: {}'.format(len(history_entries)))

    #     for history in history_entries:
    #         self._add_to_history(history.link, history.user_id)

    #         self.logger.info('Recovered: {}'.format(history))

    #         if link not in self.full_news_list:

    #             self.full_news_list.append(
    #                 history.link,
    #             )

    # def _recovery_last_news(self):

    def _is_db_cached(self, link):
        news_entries = self.db_session.query(NewsLink) \
            .filter_by(link=link).one_or_none()
        return news_entries is not None

    def _cache_2_db(self, news_list):
        if not news_list:
            return

        for news in news_list:
            db_entry = NewsLink(link=news.link, ts=news.ts)
            self.db_session.add(db_entry)

        self.db_session.commit()
        self.logger.info('Commited to database')

    def _print_history(self):
        self.logger.info('--- History ---')
        history_entries = self.db_session.query(ReadHistory).all()
        for history in history_entries:
            self.logger.info('{}'.format(history))

    def _print_news_table(self):
        self.logger.info('--- News Links ---')
        news_entries = self.db_session.query(NewsLink).all()
        for news in news_entries:
            self.logger.info('{}'.format(news))

    def _commit_2_history_db(self, news_db_entry, user_id):
        history_db_entry = ReadHistory(link_id=news_db_entry.id,
                                       user_id=user_id)
        self.db_session.add(history_db_entry)
        self.db_session.commit()

        self.logger.info('Commited to database')

    def _get_last_fresh_news(self, user_id):
        subquery = self.db_session.query(ReadHistory.link_id).filter(ReadHistory.user_id == user_id).all()
        new_history_entries = self.db_session.query(NewsLink) \
            .filter(~NewsLink.id.in_(subquery)) \
            .order_by(NewsLink.ts.desc()) \
            .first()

        return new_history_entries

    def _is_in_history(self, link, id_):
        if id_ not in self.readed_news:
            return False

        if link not in self.readed_news[id_]:
            return False

        return True

    def _update_last_news(self):
        news_2_cache = []

        self.logger.info('Called _update_last_news()')

        for source in self.sources:
            news_list = source.get_last_news()
            for news in news_list:
                if self._is_db_cached(news.link):
                    continue

                ts = source.get_time(news.link)
                news.set_time(ts)

                self.logger.info(
                    'Received news: {}'.format(news.link, news.ts))

                news_2_cache.append(news)

            print('Source end')

        self._cache_2_db(news_2_cache)

    def get_last_fresh_news(self, user_id):
        self._update_last_news()

        fresh_news = self._get_last_fresh_news(user_id)
        if fresh_news is None:
            return None

        self._commit_2_history_db(fresh_news, user_id)

        return fresh_news.link


class GovNewsParser:
    def __init__(self):
        self.url = 'https://edu.gov.ru/press/news/'

    def get_last_news(self):
        response = requests.get(self.url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        links = []

        for news in content.find_all("div", {"class": "row mb2"}):
            reference = news.find("a")
            link = reference['href']
            links.append(
                NewsRecord(link)
            )

        return links

    def get_time(self, url):
        response = requests.get(url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        date_str = content.find("div", {'class': 'date'}).text
        date_str = date_str.strip()

        ts = dateparser.parse(date_str).timestamp()

        return ts


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = GovNewsParser()

    # news = parser.get_news()
    # print(news)

    stream = StreamingNews(sources=[parser])

    stream._print_history()
    stream._print_news_table()

    news = stream.get_last_fresh_news(6)

    # for i in range(5):
    # print(stream.get_news(6))
