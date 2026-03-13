import scrapy


class ScrapedWebsite(scrapy.Item):
    url = scrapy.Field()
    email = scrapy.Field()
    body_text = scrapy.Field()
