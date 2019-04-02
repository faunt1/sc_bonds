# -*- coding: utf-8 -*-
import scrapy
import re

code_range_str = '110000-110099|113000-113099|113500-113599|123000-123099|127000-127099|128000-128099|132000-132099'
#code_range_str = '123007'

#http://money.finance.sina.com.cn/bond/conversion/sz128038.html
base_url = 'http://money.finance.sina.com.cn/bond/conversion/'

class AdjustPriceSpider(scrapy.Spider):
    name = "cb_adjust_convert_price"
    
    def start_requests(self):
        #yield scrapy.Request('http://www.example.com/1.html', self.parse)
    
        code_range_list = code_range_str.split("|")    
        for code_range in code_range_list:
            codes = code_range.split("-")
            if(not codes[0].isdigit()):
                break
            start_code = (int) (codes[0])
            if(len(codes) > 1):
                end_code = (int) (codes[1]) + 1
            else:
                end_code = start_code + 1
            for i in range(start_code, end_code):
                code = (str)(i)
                m_code ='sh%s'%code if code[:1] in ['5', '6', '9'] or code[:2] in ['11', '13'] else 'sz%s'%code

                url = base_url + m_code + '.html'
                yield scrapy.Request(url, meta={'code': code}, callback=self.parse)
        
    
    def parse(self, response):
        code = response.meta['code']
        name = response.xpath('//span[@class="bluetit"]/a[1]/text()').extract()
        
        #找到div[text()='转股价变动'后面的那个table
        table = response.xpath("//div[text()='转股价变动']/following-sibling::table[1]")
 
        names = table.xpath('.//tr[@class="bluetit"]//text()').extract()                #['序号', '价格变动类型', '公告日期', '转股价格生效日期', '执行日期', '转股价格（元）', '转股比例（%）']
        values_sel = table.xpath('.//tr[@class="bluecnt"]')

        for sel in values_sel:
            item = {
                'code':code, 
                'name':name
            }
            if len(names) == 7:
                #将名字换成英文，后续好操作
                names = ['num', 'adj_type', 'pub_dt', 'ef_dt', 'exec_dt', 'convert_price', 'cvt_rt']
            values = sel.xpath('.//text()').extract()            
            sub_values = dict(zip(names, values))
            #print(sub_values, '...........', sub_values)
            item.update(sub_values)
            #print('___________', item)
            yield item
            

