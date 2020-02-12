import logging
import os
import time
import concurrent.futures

import datetime

import dateparser
import requests
from bs4 import BeautifulSoup
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

    def __repr__(self):
        return 'NewsRecord<link={}, ts={}>' \
            .format(self.link, self.ts)


class StreamingNews:
    def __init__(self, sources):
        self.news_map = {}
        self.readed_news = {}
        self.full_news_list = []
        self.sources = sources
        self.logger = logging.getLogger(self.__class__.__name__)

        self.db_session = Session()
        self.last_update_time = 0

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
        subquery = self.db_session.query(ReadHistory.link_id).filter(
            ReadHistory.user_id == user_id).all()
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

        links_2_get_info = {}

        for source in self.sources:
            links = source.get_last_news_links()
            for link in links:
                if self._is_db_cached(link):
                    continue

                links_2_get_info[link] = source

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(source.get_time, source, link): link
                             for link, source in links_2_get_info.items()}

            for future in concurrent.futures.as_completed(future_to_url):
                link = future_to_url[future]
                ts = future.result()

                news = NewsRecord(link=link, ts=ts)
                self.logger.info('Received: {}'.format(news))

                news_2_cache.append(news)

            print('Source end')

        self._cache_2_db(news_2_cache)

    def get_last_fresh_news(self, user_id):
        if time.time() - self.last_update_time > 5*60:
            self._update_last_news()
            self.last_update_time = time.time()

        fresh_news = self._get_last_fresh_news(user_id)
        if fresh_news is None:
            return None

        self._commit_2_history_db(fresh_news, user_id)

        return fresh_news.link


class GovNewsParser:
    def __init__(self):
        self.url = 'https://edu.gov.ru/press/news/'

    def get_last_news_links(self):
        response = requests.get(self.url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        links = []

        for news in content.find_all("div", {"class": "row mb2"}):
            reference = news.find("a")
            link = reference['href']
            links.append(
                link
            )

        return links

    def get_time(self, url):
        response = requests.get(url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        date_str = content.find("div", {'class': 'date'}).text
        date_str = date_str.strip()

        # Set GMT
        date_str = date_str + ' +0300'

        ts = dateparser.parse(date_str).timestamp()

        return ts


class EduLenoblNewsParser:
    def __init__(self):
        self.url = 'http://edu.lenobl.ru/ru/about/news/'

        self.link_root_url = 'http://edu.lenobl.ru'

    def get_last_news_links(self):
        response = requests.get(self.url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        links = []

        for news in content.find_all("div", {"class": "col-md-6"}):
            reference = news.find("a", {"class": "item"})
            link = reference['href']

            link = self.link_root_url + link
            links.append(
                link
            )

        return links

    def get_time(self, url):
        response = requests.get(url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        date_str = content.find("div", {'class': 'time'}).text
        date_str = date_str.strip()

        # Set GMT
        date_str = date_str + ' +0300'

        ts = dateparser.parse(date_str).timestamp()

        # Correction to get middle of day
        ts += 60 * 60 * 12

        return ts


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = GovNewsParser()
    parser_2 = EduLenoblNewsParser()

    news = parser_2.get_last_news()

    # for news_entry in news:
    #     news_entry.ts = parser_2.get_time(news_entry.link)
    #     print(news_entry)

    # stream = StreamingNews(sources=[parser])

    # stream._print_history()
    # stream._print_news_table()

    # news = stream.get_last_fresh_news(6)
