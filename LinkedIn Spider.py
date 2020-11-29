# encoding=utf-8
# ----------------------------------------
# 语言：Python3.9
# ----------------------------------------

import os
import time
import copy
from urllib.parse import unquote, quote
import csv

import requests
import re

LINKS_FINISHED = []  # 已抓取的linkedin用户


def login(laccount, lpassword):
    """ 根据账号密码登录linkedin """
    client = requests.Session()

    HOMEPAGE_URL = 'https://www.linkedin.com'
    LOGIN_URL = 'https://www.linkedin.com/uas/login-submit'

    html = client.get(HOMEPAGE_URL).text
    csrf = re.findall('"loginCsrfParam" value="(.*?)"', html)

    login_information = {
        'session_key': laccount,
        'session_password': lpassword,
        'loginCsrfParam': csrf[0],
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
        write_csv(employee, company_name)
        print("employee done")
    else:
        print("not a valid employee")


def write_csv(result_employee, company_name):
    """ 将结果写入CSV文件 """
    filename = company_name + ' result.csv'
    fieldnames = ["First Name", "Last Name", "Occupation", "Location", "LinkedIn-url"]
    if not os.path.isfile(filename):
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(result_employee)
    else:
        with open(filename, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(result_employee)


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
        else:
            print("already exists")
    except Exception as e:
        pass


if __name__ == '__main__':
    laccount = input('Input account email:')
    lpassword = input('Input account password:')
    s = login(laccount=laccount, lpassword=lpassword)
    company_name = input('Input the company you want to crawl:')

    url = 'https://www.google.com/search?q=%7C+Linkedin+' + quote(
        company_name) + '+site%3Anz.linkedin.com'
    results = []
    failure = 0
    if len(url) > 0 and failure < 10:
        try:
            r = requests.get(url, timeout=10)
        except Exception as e:
            failure += 1
            print('failure + 1 because of exception')
        if r.status_code == 200:
            hrefs = re.findall("https://nz\..*?\&", r.text)
            for href in hrefs:
                href = href.replace("&", "")
                href = href.replace("nz.linkedin.com", "www.linkedin.com")
                employee = crawl(href, copy.deepcopy(s))
                time.sleep(5)
            results += hrefs
            failure = 0
        else:
            failure += 2
            print(r.text)
            print('search failed: %s' % r.status_code)
    if failure >= 10:
        print('search failed: %s' % url)