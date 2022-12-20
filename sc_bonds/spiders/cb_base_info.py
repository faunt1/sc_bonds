# -*- coding: utf-8 -*-
import re

import scrapy

zz_name_code_pattern = re.compile(" >> (.*) - (\d{6})")
gp_name_code_pattern = re.compile("(.*) - (\d{6})")

zz_name_q_pattern = re.compile(" >> (.*)")
zz_code_q_pattern = re.compile(" - (\d{6})")

reb = re.compile('\s+')

code_range_str = '110000-110099|111000-111099|113000-113099|113500-113699|118000-118099|120000-120099|123000-123199|127000-127099|128000-128199|132000-132099'
# code_range_str = '113065|132015|113576|113009|132026'

#code_range_str = '128013'
base_url = 'https://www.jisilu.cn/data/convert_bond_detail/'

class BoncsBaseSpider(scrapy.Spider):
    name = "cb_base_info"

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
                url = base_url + code
                yield scrapy.Request(url, self.parse)


    def remove_empty(self, values, more=['R', 'Q', '[已退市]']):
        values = [x.strip() for x in values]
        values = [x for x in values if x != '' and x not in more]
        return values


    def parse(self, response):
        tcdata = response.css("table.jisilu_tcdata")

        if(len(tcdata) != 0):
            jisilu_nav = tcdata.css("td.jisilu_nav")        #['<td colspan="8" class="jisilu_nav"><a href="/data/cbnew/">可转债</a> &gt;&gt; 德尔转债 - 123011\t\t\t (正股：<a href="/data/stock/300473">德尔股份 - 300473</a>)\n\t\t\t \t\t\t </td>']

            names = jisilu_nav.css('::text').extract()
            names = self.remove_empty(names, more=[])

            type_Q = True if 'Q' in names else False
            type_TS = True if '[已退市]' in names else False

            names = self.remove_empty(names)
            # print(f'names:{names}, 长度{len(names)}')

            zz_name = names[0]
            zz_code = names[1]
            gp_name = names[3]
            gp_code = names[4]

            # print(f'取出的值:{zz_name}, {zz_code}, {gp_name}, {gp_code}, Q: {type_Q}, 退市: {type_TS}')
            #1. 基本数据
            main_values ={
                'zz_code':  zz_code,
                'zz_name':  zz_name,
                'gp_code':  gp_code,
                'gp_name':  gp_name,
                'type_Q':  type_Q,
                'type_TS':  type_TS
            }

            #2. 价格等关键数据
            key_values = tcdata.xpath('.//td[@class="jisilu_subtitle"]//text()').extract()
            key_values = self.remove_empty(key_values)
            # ['价格 ', '106.101', '转股价值 82.32                                    ', '到期税前收益 -1.23%', '成交(万) 388.59', '涨幅 ', '-0.25%', ' 溢价率 28.95%', '到期税后收益 -1.25%', '换手率 0.04%']
            # print(f'...........key_values:{key_values}')

            names = ['price', 'conv_value', 'ebt', 'amt', 'inc', 'discount', 'eat']

            i = 0
            j = 0
            while i < len(key_values) and j < len(names):
                name = names[j]
                if ' ' in key_values[i]:
                    value = key_values[i].split(' ')[1]
                else:
                    i += 1
                    value = key_values[i]
                i += 1
                j += 1
                main_values.update({name: value})

            #3. 转股日期等其他数据
            #获取其它字段(注意：<td id='convert_cd'><span style="color:red">未到转股期</span></td>这种情况需要//text()获取正文
            names = tcdata.xpath('.//td[@id]/@id').extract()

            #values = tcdata.xpath('.//td[@id]//text()').extract()
            #本来可以只用上面一句话搞定，由于可能某个值为空，导致会少一个text()，只能一个个取，取到None的转成''
            values_sels = tcdata.xpath('.//td[@id]')
            values = []
            for sel in values_sels:
                value = sel.xpath('text()').extract_first()
                if not value:
                    value = ''
                value = re.sub(reb,'',value)
                values.append(value)

            # print('---------names:', names, '..............values:', values)

            sub_values = dict(zip(names, values))
            cpn_desc = sub_values.get('cpn_desc')

            main_values.update(sub_values)
            # print(main_values)

            #将税前、随后联系加入
            reg_pct = re.compile("(\d+\.?\d*|\.\d+)%", re.MULTILINE)
            ret_pre_tax = re.findall(reg_pct, cpn_desc)
            ret_pre_tax = [float(i) for i in ret_pre_tax]

            #不满6个，拿第一个不满6个
            if len(ret_pre_tax) == 0:
                ret_pre_tax = [0 for i in range(6)]
            elif len(ret_pre_tax) < 6:
                ret_pre_tax = [ret_pre_tax[0] for i in range(6-len(ret_pre_tax))] + ret_pre_tax

            redeem_price = float(sub_values.get('redeem_price'))
            ret_pre_tax[-1] = redeem_price - 100
            ret_after_tax = [i*100*0.8/100 for i in ret_pre_tax]
            main_values.update({'ret_pre_tax': str(ret_pre_tax)[1:-1]})
            main_values.update({'ret_after_tax': str(ret_after_tax)[1:-1]})

            # print(main_values)

            yield main_values


