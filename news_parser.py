from bs4 import BeautifulSoup
import dateparser
import requests
import logging

from sqlalchemy import Column, Integer, String, UniqueConstraint, Float

from db_base import Base, engine, Session


class ReadHistory(Base):
    __tablename__ = 'read_history'

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer)
    link = Column(String)
    __table_args__ = (
        UniqueConstraint('user_id', 'link', name='_history_location_'),
    )

    def __init__(self, user_id, link):
        self.user_id = user_id
        self.link = link

    def __repr__(self):
        return "<ReadHistory(user_id='{}', fullname='{}')>".format(self.user_id, self.link)


class NewsLink(Base):
    __tablename__ = 'news_links'

    id = Column(Integer, autoincrement=True, primary_key=True)
    link = Column(String, unique=True)
    ts = Column(Float)

    def __init__(self, link, ts):
        self.link = link
        self.ts = ts

    def __repr__(self):
        return "<NewsLink(link='{}', ts='{}')>".format(self.link, self.ts)


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
        self._recovery_history()

    def _recovery_history(self):
        history_entries = self.db_session.query(ReadHistory).all()

        self.logger.info('Recovery len: {}'.format(len(history_entries)))

        for history in history_entries:
            self._add_to_history(history.link, history.user_id)

            self.logger.info('Recovered: {}'.format(history))

            if link not in self.full_news_list:

                self.full_news_list.append(
                    history.link,
                )

    def _add_to_history(self, link, id_):
        if id_ not in self.readed_news:
            self.readed_news[id_] = [link]
        elif link not in self.readed_news[id_]:
            self.readed_news[id_].append(link)
        else:
            return

    def _commit_to_db(self, link, id_):
        history_db_entry = ReadHistory(id_, link, )
        self.db_session.add(history_db_entry)
        self.db_session.commit()

        self.logger.info('Commited to database')

    def _is_in_history(self, link, id_):
        if id_ not in self.readed_news:
            return False

        if link not in self.readed_news[id_]:
            return False

        return True

    def get_news(self, id_):
        for source in self.sources:
            news_list = source.get_news()

            for news in news_list:
                if news.link in self.full_news_list:
                    continue

                ts = source.get_time(news.link)
                news.set_time(ts)

                self.full_news_list.append(news)

        self.full_news_list = \
            sorted(self.full_news_list, key=lambda x: -x.ts)

        for news in self.full_news_list:
            link = news.link
            if self._is_in_history(link, id_):
                continue

            self._add_to_history(link, id_)

            self.logger.info('Sending link {} to user {}'.format(
                link, id_
            ))

            self._commit_to_db(link, id_)
            return link

        return None


class GovNewsParser:
    def __init__(self):
        self.url = 'https://edu.gov.ru/press/news/'

    def get_news(self):
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

    news = parser.get_news()
    print(news)

    stream = StreamingNews(sources=[parser])

    for i in range(5):
        print(stream.get_news(6))
