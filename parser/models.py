import os
import csv
from datetime import datetime, timedelta

import asyncio
import pyppeteer
import pandas as pd
from requests_html import HTMLSession, AsyncHTMLSession

from django.db import models
from django.core.files import File


class Company(models.Model):

    name = models.CharField(max_length=256,
                            unique=True)
    file_csv = models.FileField(blank=True,
                                null=True)
    file_news = models.FileField(blank=True,
                                 null=True)

    def _get_finance_filenames(self):
        file_in = f'{self.name}-in-temp.csv'
        file_out = f'{self.name}-out-temp.csv'
        return file_in, file_out

    def _prepare_finance(self):
        file_in, file_out = self._get_finance_filenames()

        with open(file_in, 'r') as read_file, open(file_out, 'w') as write_file:
            dict_reader = csv.DictReader(read_file)
            field_names = dict_reader.fieldnames
            field_names.append('3day_before_change')
            dict_writer = csv.DictWriter(write_file, field_names)
            dict_writer.writeheader()

            for row in dict_reader:
                df = pd.read_csv(file_in)
                date_row = datetime.strptime(row['Date'], '%Y-%m-%d').date()
                date_before = date_row - timedelta(days=3)

                row_before = df.query(f'Date == "{date_before}"')
                close_row = float(row['Close'])
                close_before = row_before.get('Close').to_list()
                close_change = close_row/close_before[0] if close_before else None

                row.update({'3day_before_change': close_change})
                dict_writer.writerow(row)

    def _save_finance(self):
        _, file_out = self._get_finance_filenames()
        with open(file_out, 'r') as file:
            self.file_csv.save(f'{self.name}.csv', File(file))

    def _prepare_news(self):
        file_temp = f'{self.name}-News-temp.csv'
        url = f'https://finance.yahoo.com/quote/{self.name}?p={self.name}'
        response = asyncio.run(Company._get_async_response(url))
        news = response.html.xpath("//div[@id='quoteNewsStream-0-Stream']//h3/a")
        with open(file_temp, 'w') as file:
            field_names = {'Link', 'Title'}
            dict_writer = csv.DictWriter(file, field_names)
            dict_writer.writeheader()
            for new in news:
                title = new.text
                link = Company.get_news_link(new.attrs['href'])
                dict_writer.writerow({'Link': link, 'Title': title})

    def _save_news(self):
        file_temp = f'{self.name}-News-temp.csv'
        filename = f'{self.name}-News.csv'
        with open(file_temp, 'r') as file:
            self.file_news.save(filename, File(file))
        os.remove(file_temp)

    def _clean_temp(self):
        list(map(lambda f: os.remove(f), self._get_finance_filenames()))

    @staticmethod
    def get_news_link(link):
        if 'http' in link:
            return link
        return f'https://finance.yahoo.com{link}'

    @staticmethod
    async def _get_async_response(url):
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        session = AsyncHTMLSession()
        browser = await pyppeteer.launch({
            'ignoreHTTPSErrors': True,
            'headless': True,
            'handleSIGINT': False,
            'handleSIGTERM': False,
            'handleSIGHUP': False
        })
        session._browser = browser
        resp_page = await session.get(url)
        await resp_page.html.arender(scrolldown=2, sleep=2)  # 1 scroll down approximately exactly 10 news
        return resp_page

    def download_finance_csv(self):
        file_in, file_out = self._get_finance_filenames()
        download_url = f"https://query1.finance.yahoo.com/v7/finance/download/{self.name}" \
                       f"?period1=0&period2={10**10}&interval=1d&events=history"

        with HTMLSession() as session:
            response = session.get(url=download_url)

        with open(file_in, 'wb') as file:
            file.write(response.content)

        self._prepare_finance()
        self._save_finance()
        self._clean_temp()

    def download_news_csv(self):
        self._prepare_news()
        self._save_news()

    def __str__(self):
        return self.name
