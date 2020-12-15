import os
import time
import copy
from urllib.parse import unquote, quote, urlencode
import csv
import getpass

import requests
import re

NAMES_FINISHED = []  # 已抓取的linkedin用户


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


def parse(content, url, log_filename, employee):
    """ 解析一个员工的Linkedin主页 """
    content = unquote(content.decode("utf-8")).replace('&quot;', '"')
    occupation = re.findall('"headline":"(.*?)"', content)
    if occupation:
        employee["Occupation"] = occupation[0]
        print('.', end='', flush=True)
    else:
        print('.', end='', flush=True)
        with open(log_filename, 'a') as f:
            f.write("not a valid employee %s\n" % url)
    time.sleep(5)


def write_csv(result_employee, company_name):
    """ 将结果写入CSV文件 """
    with open(company_name, 'a', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(result_employee)


def crawl(url, s, log_filename, employee):
    """ 抓取每一个搜索结果 """
    try:
        failure = 0
        while failure < 10:
            try:
                r = s.get(url, timeout=100)
            except Exception as e:
                failure += 1
                continue
            if r.status_code == 200:
                parse(r.content, url, log_filename, employee)
                break
            else:
                print('.', end='', flush=True)
                with open(log_filename, 'a') as f:
                    f.write('%s %s\n' % (r.status_code, url))
                failure += 2
        if failure >= 10:
            print('.', end='', flush=True)
            with open(log_filename, 'a') as f:
                f.write('Failed: %s\n' % url)
        else:
            print('.', end='', flush=True)
            with open(log_filename, 'a') as f:
                f.write("already exists : %s\n" %url)
    except Exception as e:
        pass


if __name__ == '__main__':
    detailed_search = input('Do you want to log in to Linkedin To get more information? Yes/No: - [default:No]\n').lower()
    if detailed_search == 'yes' or detailed_search == 'y':
        detailed_search = True
        laccount = input('Input account email:')
        lpassword = getpass.getpass('Input account password:')
        s = login(laccount=laccount, lpassword=lpassword)
    else:
        detailed_search = False
    company_name = input('Input the company name:')
    print('Application is preparing data now', end='', flush=True)
    log_filename = company_name+'log.txt'
    company_filename = company_name + ' result.csv'
    num_of_fail_occupation_employee = 0
    results = []
    num_of_results = 1
    failure = 0
    page = 0
    with open(company_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["Name", "Occupation", "LinkedIn-url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    while num_of_results != len(results) and page < 10:
        num_of_results = len(results)
        url = 'https://www.google.com/search?q=' + quote(
            company_name) + '+site%3Anz.linkedin.com&start=' + str(page * 10)
        if len(url) > 0 and failure < 10:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    employees = re.findall('<a href="/url\?q=(https://nz.linkedin.com/in/.*?)[\/]?&amp.*?><h3 class="zBAuLc"><div class="BNeawe vvjwJb AP7Wnd">(.*?)[\s]?-[\s](.*?)[\s]?[\-\|][\s]?(.*?)</div>', r.text)
                    for index in range(len(employees)):
                        employee = employees[index]
                        nameindex = employee[1].rfind(">")
                        employee_name = employee[1][nameindex + 1:]
                        if company_name.lower() in employee[3].lower():
                            titleoccupation = True
                            companyindex = max(employee[3].rfind('%s' %s) for s in ('-', '|', '.'))
                            occupation = employee[2]
                            company_to_check = employee[3][:companyindex]
                        else:
                            titleoccupation = False
                            additional_search = re.findall('(?i)%s [\|](.*?) at %s' %(employee_name, company_name), r.text)
                            company_to_check = employee[2]
                            if additional_search:
                                additional_searchindex = max(additional_search[0].rfind('%s' % s) for s in ('.', '|'))
                                additional_search = additional_search[0][additional_searchindex+1:]
                        if company_to_check.strip().lower() == company_name.strip().lower():
                            if titleoccupation:
                                employee_result = {"Name": employee_name, "Occupation":
                                    occupation, "LinkedIn-url": employee[0]}
                            elif additional_search and not titleoccupation:
                                employee_result = {"Name": employee_name, "Occupation":
                                    additional_search, "LinkedIn-url": employee[0]}
                            elif detailed_search and not titleoccupation:
                                employee_result = {"Name": employee_name, "Occupation":
                                    " ", "LinkedIn-url": employee[0]}
                                employee_result['LinkedIn-url'] = employee_result['LinkedIn-url'].replace("nz.linkedin.com", "www.linkedin.com")
                                crawl(employee_result['LinkedIn-url'], copy.deepcopy(s), log_filename, employee_result)
                            elif not titleoccupation:
                                employee_result = {"Name": employee_name, "Occupation":
                                " ", "LinkedIn-url": employee[0]}
                                num_of_fail_occupation_employee += 1
                            if employee_name not in NAMES_FINISHED:
                                NAMES_FINISHED.append(employee_name)
                                results.append(employee_result["LinkedIn-url"])
                                write_csv(employee_result, company_filename)
                else:
                    failure += 2
                    print('.', end='', flush=True)
                    with open(log_filename, 'a') as f:
                        f.write('search failed: %s %s\n' % (r.status_code, url))
            except Exception as e:
                failure += 1
                print('.', end='', flush=True)
                print(e)
                with open(log_filename, 'a') as f:
                    f.write('failure + 1 because of exception %s\n' % url)
            failure = 0
            page += 1
            print('.', end='', flush=True)
            time.sleep(1)
        if failure >= 10:
            print('.', end='', flush=True)
            with open(log_filename, 'a') as f:
                f.write('search failed: %s\n' % url)
    print()
    with open(log_filename, 'a') as f:
        f.write('Total employees on linkedin: ' + str(len(results)) + '\n')
        f.write('Employees without occupation: '+str(num_of_fail_occupation_employee) + '\n')
    print("Data is written to " + company_name + ' result.csv file', flush=True)
    input("Press anything to exit")
