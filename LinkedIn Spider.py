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
    return client


def parse(content, url):
    """ 解析一个员工的Linkedin主页 """
    content = unquote(content.decode("utf-8")).replace('&quot;', '"')
    employee = {"LinkedIn-url": url}
    firstname = re.findall('"multiLocaleFirstName":{.*?:(.*?)}', content)
    lastname = re.findall('"multiLocaleLastName":{.*?:(.*?)}', content)
    if firstname and lastname:
        employee["First Name"] = firstname[1]
        employee["Last Name"] = lastname[1]

        occupation = re.findall('"headline":"(.*?)"', content)
        if occupation:
            employee["Occupation"] = occupation[0]

        locationName = re.findall('"locationName":"(.*?)"', content)
        if locationName:
            employee["Location"] = locationName[0]
        else:
            employee.append(" ")
        print(employee)
        RESULT.append(employee)


def write_csv(result_list):
    """ 将结果写入CSV文件 """
    with open('result.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["First Name", "Last Name", "Occupation", "Location", "LinkedIn-url"]
        filewriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
        filewriter.writeheader()
        filewriter.writerows(result_list)


def crawl(url, s):
    """ 抓取每一个搜索结果 """
    try:
        if len(url) > 0 and url not in LINKS_FINISHED:
            LINKS_FINISHED.append(url)

            failure = 0
            while failure < 10:
                try:
                    r = s.get(url, timeout=10)
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
    s = login(laccount='1850806727@qq.com', lpassword='ywsa,7939')  # 测试账号
    company_name = input('Input the company you want to crawl:')

    for page in range(0, 5):
        url = 'https://www.google.com/search?q=%7C+Linkedin+' + quote(
            company_name) + '+site%3Anz.linkedin.com&start=' + str(page * 10)
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
                soup = BeautifulSoup(r.content, 'html.parser')
                hrefs = re.findall("https://nz\..*?\&", r.text)
                for href in hrefs:
                    href = href.replace("&", "")
                    href = href.replace("nz.linkedin.com", "www.linkedin.com")
                    crawl(href, copy.deepcopy(s))
                results += hrefs
                tree = etree.HTML(r.content)
                nextpage_txt = tree.xpath('//div[@id="page"]/a[@class="n" and contains(text(), "next")]/@href')
                url = 'http://www.google.com' + nextpage_txt[0].strip() if nextpage_txt else ''
                failure = 0
            else:
                failure += 2
                print('search failed: %s' % r.status_code)
    write_csv(RESULT)
    if failure >= 10:
        print('search failed: %s' % url)
