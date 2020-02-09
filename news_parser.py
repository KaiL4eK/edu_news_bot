import requests

from bs4 import BeautifulSoup




class GovNewsParser:
    def __init__(self):
        self.url = 'https://edu.gov.ru/press/news/'

    def get_news(self):
        response = requests.get(self.url)

        root_soup = BeautifulSoup(response.content, 'lxml')

        contents = root_soup.find("div", id="content")

        links = []

        for news in contents.find_all("div", {"class": "row mb2"}):
            reference = news.find("a")

            links.append(reference['href'])

        return links

if __name__ == '__main__':
    parser = GovNewsParser()

    news = parser.get_news()

    print(news)
