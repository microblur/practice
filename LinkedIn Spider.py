# encoding=utf-8
# ----------------------------------------
# 语言：Python3.9
# ----------------------------------------

import copy
# from googlesearch import search
from urllib.parse import unquote, quote
from bs4 import BeautifulSoup
import csv

import requests
import re
from lxml import etree
LINKS_FINISHED = []  # 已抓取的linkedin用户
RESULT = []


def login(laccount, lpassword):
    """ 根据账号密码登录linkedin """
    client = requests.Session()

    HOMEPAGE_URL = 'https://www.linkedin.com'
    LOGIN_URL = 'https://www.linkedin.com/uas/login-submit'

    html = client.get(HOMEPAGE_URL).content
    soup = BeautifulSoup(html, "html.parser")
    csrf = soup.find('input', {'name': 'loginCsrfParam'}).get('value')

    login_information = {
        'session_key': laccount,
        'session_password': lpassword,
        'loginCsrfParam': csrf,
        'trk': 'guest_homepage-basic_sign-in-submit'
    }

    client.post(LOGIN_URL, data=login_information)
    client.get(HOMEPAGE_URL)

    #response = client.get('')
    return client


def get_linkedin_url(url, s):
    """ 百度搜索出来的是百度跳转链接，要从中提取出linkedin链接 """
    try:
        r = s.get(url, allow_redirects=False)
        if r.status_code == 302 and 'Location' in r.headers.keys() and 'linkedin.com/in/' in r.headers['Location']:
            return r.headers['Location']
    except Exception as e:
        print('get linkedin url failed: %s' % url)
    return ''


def parse(content, url):
    """ 解析一个员工的Linkedin主页 """
    content = unquote(content.decode("utf-8")).replace('&quot;', '"')
    employee = list()
    # contact_content = unquote(contact_content.decode("utf-8"))

    # profile_txt = ' '.join(re.findall('(\{[^\{]*?profile\.Profile"[^\}]*?\})', content))
    firstname = re.findall('"multiLocaleFirstName":{.*?:(.*?)}', content)
    lastname = re.findall('"multiLocaleLastName":{.*?:(.*?)}', content)
    if firstname and lastname:
        employee.append(firstname[1])
        employee.append(lastname[1])

        occupation = re.findall('"headline":"(.*?)"', content)
        if occupation:
            employee.append(occupation)

        locationName = re.findall('"locationName":"(.*?)"', content)
        if locationName:
            employee.append(locationName)
        employee.append(url)
        RESULT.append(employee)


def write_csv(result_list):
    with open('result.csv', 'w') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        fieldnames = ["First Name", "Last Name", "Occupation", "Location", "LinkedIn-url"]
        filewriter.writerow(fieldnames)
        filewriter.writerows(result_list)


def crawl(url, s):
    """ 抓取每一个搜索结果 """
    try:
        url = get_linkedin_url(url, copy.deepcopy(s)).replace('cn.linkedin.com', 'www.linkedin.com')  # 百度搜索出的结果是百度跳转链接，要提取出linkedin的链接。
        if len(url) > 0 and url not in LINKS_FINISHED:
            LINKS_FINISHED.append(url)

            failure = 0
            while failure < 10:
                try:
                    r = s.get(url, timeout=10)
                    contact_url = url+'/detail/contact-info/'
                    contact_r = s.get(contact_url, timeout=10)
                except Exception as e:
                    failure += 1
                    continue
                if r.status_code == 200:
                    parse(r.content, url)
                    break
                else:
                    print('%s %s' % (r.status_code, url))
                    failure += 2
            if failure >= 10:
                print('Failed: %s' % url)
    except Exception as e:
        pass


if __name__ == '__main__':
    s = login(laccount='danialhong97@gmail.com', lpassword='Imba0706')  # 测试账号
    company_name = input('Input the company you want to crawl:')
    maxpage = 50  # 抓取前50页百度搜索结果，百度搜索最多显示76页

    # 百度搜索
    url = 'http://www.baidu.com/s?ie=UTF-8&wd=%20%7C%20领英%20' + quote(company_name) + '%20site%3Alinkedin.com'
    print(url)
    results = []
    failure = 0
    while len(url) > 0 and failure < 10:
        try:
            r = requests.get(url, timeout=10)
        except Exception as e:
            failure += 1
            print('failure + 1 because of exception')
            continue
        if r.status_code == 200:
            hrefs = list(set(re.findall('"(http://www\.baidu\.com/link\?url=.*?)"', r.content.decode('utf-8'))))  # 一页有10个搜索结果
            for href in hrefs:
                crawl(href, copy.deepcopy(s))
            results += hrefs
            tree = etree.HTML(r.content)
            nextpage_txt = tree.xpath('//div[@id="page"]/a[@class="n" and contains(text(), "下一页")]/@href')
            url = 'http://www.baidu.com' + nextpage_txt[0].strip() if nextpage_txt else ''
            failure = 0
            maxpage -= 1
            if maxpage <= 0:
                break
        else:
            failure += 2
            print('search failed: %s' % r.status_code)
    write_csv(RESULT)
    if failure >= 10:
        print('search failed: %s' % url)