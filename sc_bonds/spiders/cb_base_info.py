# -*- coding: utf-8 -*-
import scrapy
import re

zz_name_code_pattern = re.compile(" >> (.*) - (\d{6})")
gp_name_code_pattern = re.compile("(.*) - (\d{6})")

zz_name_q_pattern = re.compile(" >> (.*)")
zz_code_q_pattern = re.compile(" - (\d{6})")

reb = re.compile('\s+') 

code_range_str = '110000-110099|113000-113099|113500-113599|123000-123099|127000-127099|128000-128099|132000-132099'
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
        
    
    def parse(self, response):
        tcdata = response.css("table.jisilu_tcdata")
        
        if(len(tcdata) != 0):            
            jisilu_nav = tcdata.css("td.jisilu_nav")        #['<td colspan="8" class="jisilu_nav"><a href="/data/cbnew/">可转债</a> &gt;&gt; 德尔转债 - 123011\t\t\t (正股：<a href="/data/stock/300473">德尔股份 - 300473</a>)\n\t\t\t \t\t\t </td>']
            name = jisilu_nav.extract()[0]
            type_Q = False
            if name.find(r">Q</sup>") != -1:
                type_Q = True
            
            type_TS = False
            if name.find('已退市') != -1:
                type_TS = True
            
            #print('name:', name)
            #print('type_Q:', type_Q, ', type_TS:', type_TS)
            names = jisilu_nav.css('::text').extract()      
            #print('names:[[{}]]'.format(names))
            if not type_Q:                 
                #如果没有type_Q，在names[0]和names[1]中
                #星源转债 - 123009			 (正股：<a href="/data/stock/300568">星源材质 - 300568
                #names[0]: 星源转债 - 123009			 (正股：
                #names[1]: 星源材质 - 300568                
                name_code = gp_name_code_pattern.match(names[0])        #"(.*) - (\d{6})"
                zz_name = name_code.group(1)      #德尔转债
                zz_code = name_code.group(2)      #123011
                
                name_code = gp_name_code_pattern.match(names[1])        #"(.*) - (\d{6})"
                gp_name = name_code.group(1)      #德尔股份   
                gp_code = name_code.group(2)      #300473
            else:
                #如果type_Q，在names[0], names[2], names[3]中                
                #新的: 17桐昆EB<sup style="color:#fda429;">Q</sup> - 132010			 (正股：<a href="/data/stock/601233">桐昆股份 - 601233
                zz_name = names[0]        # 17桐昆EB
                zz_code = zz_code_q_pattern.match(names[2]).group(1)        #" - (\d{6})"
                
                name_code = gp_name_code_pattern.match(names[3])        #"(.*) - (\d{6})"
                gp_name = name_code.group(1)      #桐昆股份
                gp_code = name_code.group(2)      #300473
  
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
            # ['价格：', '100.18', '转股价值：104.63', '税前收益：2.28%', '成交(万)：33450.89', '涨幅：', '1.23%', '溢价率：-4.25%', '税后收益：1.82%', '剩余年限：5.581']

            names = ['price', 'conv_value', 'ebt', 'amt', 'inc', 'discount', 'eat', 'remain_y']
            
            i = 0
            j = 0
            while i < len(key_values):
                name = names[j]
                if key_values[i][-1] == '：':                    
                    i += 1
                    value = key_values[i]
                else:
                    value = key_values[i].split('：')[1]
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
            
            #print('---------names:', names, '..............values:', values)
            
            sub_values = dict(zip(names, values))
            cpn_desc = sub_values.get('cpn_desc')
            
            main_values.update(sub_values)
            #print(main_values)
            
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
            
            #print(main_values)
            
            yield main_values
            

