import requests

from bs4 import BeautifulSoup

import datetime
import locale
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


class StreamingNews:
    def __init__(self, sources):
        self.news_map = {}
        self.readed_news = {}
        self.full_news_list = []
        self.sources = sources

    def get_news(self, id_):

        for source in self.sources:
            links = source.get_news()

            for link, ts in links:
                if link in self.full_news_list:
                    continue

                self.full_news_list.append(
                    (link, ts)
                )

        self.full_news_list = \
            sorted(self.full_news_list,
                   key=lambda x: x['time'])

        for news in self.full_news_list:
            link = news[0]
            if link in self.readed_news[id_]:
                continue

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
            date = self._get_time(link)

            links.append(
                (link, date)
            )

        return links

    def _get_time(self, url):
        response = requests.get(url)
        root_soup = BeautifulSoup(response.content, 'lxml')
        content = root_soup.find("div", id="content")

        date_str = content.find("div", {'class': 'date'}).text
        date_str = date_str.strip()

        date = datetime.datetime.strptime(date_str, u'%d %B %Y, %H:%M')
        ts = date.timestamp()

        print(ts)

        return ts


if __name__ == '__main__':
    parser = GovNewsParser()

    news = parser.get_news()

    print(news)
