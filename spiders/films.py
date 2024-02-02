import scrapy
from wiki_parser.items import MovieItem  
import re

def clean_string(text):
    ## если запарсили что-то плохое
    # Удаление последовательностей вида [что-угодно]
    text = re.sub(r'\[\w*\]', '', text)
    
    # Удаление спецсимволов (например, неразрывных пробелов)
    text = re.sub(r'\xa0', ' ', text)
    
    # Замена двойных пробелов на одинарные
    text = re.sub(r'\s+', ' ', text)
    
    # Удаление пробелов перед запятыми
    text = re.sub(r'\s+,', ',', text)
    
    return text.strip()

class MoviesSpider(scrapy.Spider):
    name = "films"
    allowed_domains = ["ru.wikipedia.org","www.imdb.com"] 
    start_urls = [
        "https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту"
    ]
    main_url = 'https://ru.wikipedia.org/'

    def parse(self, response): 
        # Извлечение ссылок на страницы фильмов
        for movie_page in response.xpath('//div[@id="mw-pages"]//a/@href').extract():
            yield response.follow(movie_page, self.parse_movie)

        #Переход на следующую страницу категории
        next_page = response.xpath('//a[contains(text(), "Следующая страница")]/@href').extract_first() 
        next_page = self.main_url+next_page
        if next_page: 
            yield response.follow( next_page, self.parse)
  

    def parse_movie(self, response):
        item = MovieItem()

     
        table_rows = response.xpath('//table[contains(@class, "infobox")]/tbody/tr')
        if len(table_rows) ==0:
            return
        for s, row in enumerate(table_rows): 
            title, genre, director, country, year = None, None, None, None, None, 
            head = row.xpath('.//th/text()').get(default='')
            head_links = row.xpath('.//th//a/text()').getall()

            if s==0:
                title = ' '.join(row.xpath('.//th//text()').getall()).strip() 
                item['title'] = clean_string(title)  

            # Проверяем, есть ли среди текстов слово "Жанр"
            if ' Жанры\n' in head_links or ' Жанр \n' in head_links: 
                genre = ' '.join(row.xpath('.//td//text()').getall()).strip() 
                item['genre'] = clean_string(genre)

            # Режиссёр
            if head == 'Режиссёр' or head == 'Режиссёры':
                director = ' '.join(row.xpath('.//td//text()').getall()).strip() 
                item['director'] = clean_string(director)

            # Страна
            if head == 'Страна' or head == 'Страны':
                country = ' '.join(row.xpath('.//td//text()').getall()).strip() 
                item['country'] = clean_string(country)

            # Год
            year = row.xpath('.//th[contains(text(), "Год")]/following-sibling::td//a/@title').re_first(r'\d{4}')
            if year:
                item['year'] = clean_string(year)
            
        
        item['imdb_rating'] = None
            
        imdb_url = response.xpath('//*[@data-wikidata-property-id="P345"]//a/@href').extract_first()

        if imdb_url :
            yield scrapy.Request(imdb_url, callback=imdb_parse, cb_kwargs={'data': item})
        else:
            yield item
                  
            

        
def imdb_parse(response, data): 
        data['imdb_rating'] = response.xpath(
            '//div[@data-testid="hero-rating-bar__aggregate-rating__score"]//text()').extract_first()   
        yield data