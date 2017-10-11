#!/usr/bin/env python
#coding:utf8
import requests
import time
import re
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from database.base_db import Session
from models.model import Company, Position, Proxys
session = Session()
class Scrapy(object):
    pages = 0
    proxies = []
    ua_list = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"
    ]
    @property
    def header(self):
        ua = random.choice(self.ua_list)
        return {
            'User-Agent': ua,
            'Referer': 'https://www.lagou.com/jobs/list_%E4%BC%9A%E8%AE%A1?labelWords=sug&fromSearch=true&suginput=%E4%BC%9A%E8%AE%A1'
        }

    def sleep(self, s):
        print('休眠:{}秒'.format(s))
        time.sleep(s)

    def __init__(self, keyword):
        self.keyword = keyword
        proxy_list = session.query(Proxys).all()
        for proxy in proxy_list:
            self.proxies.append({
                'http': 'http://{}:{}'.format(proxy.ip, proxy.port)
            }) 

    def fetch_one(self, page=0):
        url = 'https://www.lagou.com/jobs/positionAjax.json?city=%E6%88%90%E9%83%BD&needAddtionalResult=false&isSchoolJob=0'
        proxy = random.choice(self.proxies)
        params = {
            'first': False,
            'pn': str(page),
            'kd': self.keyword
        }
        try:
            result = requests.post(url, data=params, headers=self.header, proxies=proxy, timeout=5).json()
        except Exception:
            proxy = random.choice(self.proxies)
            result = requests.post(url, data=params, headers=self.header, proxies=proxy, timeout=10).json()

        if result['success'] == False:
            print(', 抓取失败')
            print(result)
            self.sleep(60)
            return self.fetch_one(page)
        
        return result
    
    def spider(self):
        result = self.fetch_one(0)
        self.pages = result['content']['positionResult']['totalCount']
        page_num = int(self.pages / 15) + 1
        if self.pages % 15 == 0:
            page_num = self.pages // 15
        print('共{}页'.format(page_num), end='')
        for page in range(1, page_num + 1):
            print(
                '正在抓取第{}页'.format(
                    page
                ),
                end=''
            )
            result = self.fetch_one(page)
            self.parse(result['content']['positionResult']['result'], page)
            self.sleep(3)
        print('{}职位抓取完成.'.format(self.keyword))
    def parse(self, jobs, page):
        for i in range(0, len(jobs)):
            job = jobs[i]
            # if position has been crawled
            cp = session.query(Company).filter_by(id=job['companyId']).first()
            ps = session.query(Position).filter_by(id=job['positionId']).first()
            if ps is None:
                while True:
                    try:
                        job_detail = self.parse_job_detail(job['positionId'])
                        break;
                    except Exception:
                        self.sleep(60)
                        job_detail = self.parse_job_detail(job['positionId'])
                position = Position(
                    id=job['positionId'],
                    company_id=job['companyId'],
                    position_name=job['positionName'],
                    work_year=job['workYear'],
                    education=job['education'],
                    job_nature=job['jobNature'],
                    create_time=job['createTime'],
                    city=job['city'],
                    industry_field=job['industryField'],
                    position_advantage=job['positionAdvantage'],
                    salary=job['salary'],
                    position_lables=job['positionLables'],
                    industry_lables=job['industryLables'],
                    district=job['district'],
                    first_type=job['firstType'],
                    second_type=job['secondType'],
                    job_advantage=job_detail['job_advantage'],
                    description=job_detail['description'],
                    location=job_detail['location'],
                    publisher_name=job_detail['publisher_name'],
                    tend_to_talk=job_detail['tend_to_talk'],
                    deal_resume=job_detail['deal_resume'],
                    active_time=job_detail['active_time']
                )
                session.add(position)
                session.commit()
            if cp is None:
                # if company has been crawled
                company = Company(
                    id=job['companyId'],
                    company_size=job['companySize'],
                    company_short_name=job['companyShortName'],
                    company_full_name=job['companyFullName'],
                    finance_stage=job['financeStage'],
                    company_label_list=job['companyLabelList']
                )
                session.add(company)
                session.commit()
            print('正在抓取第{}页，第{}条记录'.format(page, i+1))
    
    def parse_job_detail(self, job_id):
        fetch_url = 'https://www.lagou.com/jobs/{}.html'.format(job_id)
        detail_driver = webdriver.Chrome()
        detail_driver.get(fetch_url)
        self.sleep(15)
        html = detail_driver.page_source
        detail_driver.close()
        soup = BeautifulSoup(html,'lxml')
        job_advantage = None
        description = None
        location = None
        publisher_name = None
        tend_to_talk = None
        deal_resume = None
        active_time = None
        # 职位诱惑
        job_advantage = soup.select('#job_detail')[0].select('.job-advantage')[0].select('p')[0].text
        # 职位描述
        
        description_tmp = soup.select('#job_detail')[0].select('dd.job_bt div')[0].select('p')
        description = [x.text for x in description_tmp if x.text != '']
        
        # 工作区域
        
        location = re.sub('[/\s查看地图]', '', soup.select('.work_addr')[0].text)
        
        
        # 发布者
        
        publisher_name = soup.select('.publisher_name .name')[0].text
        
        
        # 聊天意愿
        
        tend_to_talk = dict()
        tend_content = soup.select('.publisher_data div')[0]
        tend_to_talk['step'] = tend_content.select('.data')[0].text
        tend_to_talk['percent'] = tend_content.select('.tip')[0].select('i')[0].text
        tend_to_talk['time'] = tend_content.select('.tip')[0].select('i')[1].text
        
        
        
        deal_resume = dict()
        resume_content = soup.select('.publisher_data div')[1]
        deal_resume['step'] = resume_content.select('.data')[0].text
        deal_resume['percent'] = resume_content.select('.tip')[0].select('i')[0].text
        deal_resume['time'] = resume_content.select('.tip')[0].select('i')[1].text
        
            
        # 活跃时间--上午，下午，中午
        
        active_time = soup.select('.publisher_data div')[1].select('.data')[0].text
        
        
        return {
            'job_advantage': job_advantage,
            'description': description,
            'location': location,
            'publisher_name': publisher_name,
            'tend_to_talk': tend_to_talk,
            'deal_resume': deal_resume,
            'active_time': active_time
        }


if __name__ == '__main__':
    # from models.model import Base, engine
    # Base.metadata.drop_all(engine)
    # Base.metadata.create_all(engine)

    pos_list = [
        '前端',
        'web前端',
        'python',
        '后端',
        '会计',
        '审计',
        '会计与审计',
        '行政',
        '出纳',
        '收纳',
        '统计',
        '数据分析',
        '爬虫',
        'office',
        'excel',
        'ppt',
        '机器学习',
        '人工智能',
        '深度学习'
    ]
    for pos in pos_list:
        print('关键字{}, '.format(pos), end='')
        scrapy = Scrapy(pos)
        scrapy.spider()
        scrapy.sleep(70)
