import requests
import re
from bs4 import BeautifulSoup
from common.error import PasswordError

class LibLogin(object):
    def __init__(self):

        self.session = requests.session()
        self.lib_login_url = 'http://202.192.41.8/NTRdrLogin.aspx'
        self.borrowed_book_url = 'http://202.192.41.8/NTBookLoanRetr.aspx'
    
    def get_view(self,response):
        '''获得模拟登陆时提交表单所需的三个参数'''
        soup = BeautifulSoup(response.text, "lxml")
        view = []
        view.append(soup.findAll(name="input")[0]["value"]) 
        view.append(soup.findAll(name="input")[1]["value"])
        view.append(soup.findAll(name="input")[2]["value"]) 
        return view
    def login(self,username,password):
        login_page = requests.get(self.lib_login_url)
        view = self.get_view(login_page)
        post_data = {
            '__VIEWSTATE':view[0],
            '__VIEWSTATEGENERATOR':view[1],
            '__EVENTVALIDATION':view[2],
            'txtName':username,
            'txtPassWord':password,
            'Logintype':'RbntRecno',
            'BtnLogin':'%E7%99%BB+%E5%BD%95'
        }
        res = self.session.post(self.lib_login_url,data=post_data,timeout = 5)
        if '密码错误' in res.text:
            #如果密码错误 则会出现PasswordError(用户名错误也会)
            raise PasswordError


class lib_num(object):

        
    def post(self,begin_time,end_time):
        '''获得图书馆进馆人数需要提交起始日期和结束日期'''
        data = {}
        data['begin'] = begin_time
        data['end'] = end_time
        res = requests.post(self.lib_url,data = data,timeout = 5)
        return  res

    def get(self):
        res = requests.get(self.lib_url,timeout = 5)
        return res

    def num_parse(self,response):
        '''利用正则表达式提取总进馆人数'''
        pattern =  re.compile('<div id=\'total\'>总进馆人次:(.*?)</div>')
        item = re.findall(pattern,response.text)
        return item[0]

    def faculty_parse(self,response):
        '''通过BeautifulSoup提取每个学院进馆人数'''
        soup = BeautifulSoup(response.text,'lxml')
        fac = soup.find_all('td',width = '300')
        fac_num={}
        for i in fac:
            fac_num[i.string] = i.find_next('td').find_next('td').string
        return fac_num


class DateTotal(lib_num):

    '''按日期查询进馆人数类'''
    
    def __init__(self,begin_time,end_time):
        self.lib_url =  'http://lib.gzhu.edu.cn:8080/bookle/goLibTotal/custom'
        self.begin_time = begin_time
        self.end_time = end_time

    def get_all(self):
        '''获得所有学院进馆人数'''
        res = self.post(self.begin_time,self.end_time)
        total_num = self.num_parse(res)
        number_data = {}
        number_data['TotalNum'] = total_num
        number_data['FacultyNum'] = self.faculty_parse(res)
        return number_data
    
    def get_total(self):
        '''获得总进馆人数'''
        res = self.post(self.begin_time,self.end_time)
        total_num = self.num_parse(res)
        number_data = {}
        number_data['TotalNum'] = total_num
        return number_data

class NowTotal(lib_num):
    '''获得当前日期进馆人数类'''

    def __init__(self):
        self.lib_url =  'http://lib.gzhu.edu.cn:8080/bookle/goLibTotal/index'


    def get_all(self):
        res = self.get()
        total_num = self.num_parse(res)
        number_data = {}
        number_data['TotalNum'] = total_num
        number_data['FacultyNum'] = self.faculty_parse(res)
        return number_data
    
    def get_total(self):
        res = self.get()
        total_num = self.num_parse(res)
        number_data = {}
        number_data['TotalNum'] = total_num
        return number_data


class LibBooks(LibLogin):


    def get_borrowed_books(self,username,password):
        self.login(username,password)
        res = self.session.get(self.borrowed_book_url)
        borrowed_books = self.parse_borrowed_books(res)
        return borrowed_books

    def parse_borrowed_books(self,response):
        '''通过BeautifulSoup提取已借书籍'''
        soup = BeautifulSoup(response.text,'lxml')
        books_name = soup.find_all('td',width = '26%')
        borrowed_books = {}
        for i in books_name:
            info = {}
            info['LoanDate'] = i.find_next_siblings('td',width='9%')[1].string 
            info['ReturnDate'] = i.find_next_siblings('td',width='9%')[2].string
            info['RenewTimes'] = i.find_next_siblings('td',width='5%')[1].string
            borrowed_books[i.string] = info
        
        return borrowed_books
    
    def renew_books(self,username,password):
        '''renew_page_url是续借页面url renew_url是发送续借请求的url
           根据所借书籍数量来决定请求链接'''
        self.login(username,password)
        renew_page_url = 'http://202.192.41.8/NTBookLoanRetr.aspx'
        renew_url = 'http://202.192.41.8/NTBookloanResult.aspx'
        res = self.session.get(renew_page_url)   
        books_code = self.get_books_code(res)
        if len(books_code) == 0:
            return {'status':'No borrowing books'}     
        elif len(books_code) == 1:
            barno = '?barno='+books_code[0]+';'
            rnbooks = self.session.get(renew_url+barno)
            status = self.get_renew_status(rnbooks)
            return status
        else:
            barno = '?barno='
            for i in books_code:
                barno = barno+'on;'
            for i in books_code:
                barno = barno+i+';'
            rnbooks = self.session.get(renew_url+barno)
            status = self.get_renew_status(rnbooks)
            return status

    def get_books_code(self,response):
        '''根据BeautifulSoup来获取续借书籍的续借码'''
        soup = BeautifulSoup(response.text,'lxml')
        books_codes_tags = soup.find_all('td',width = '14%')
        books_code = []
        for i in books_codes_tags:
            books_code.append(i.string)
        return books_code
    def get_renew_status(self,response):
        '''根据续借请求返回的网页来确定续借成功与否'''
        soup = BeautifulSoup(response.text,'lxml')
        books_name_tags = soup.find_all('td',width = '26%')
        status = {}
        for i in books_name_tags:
            status_string = i.find_previous_sibling('td',width="9%").b.font.string
            if status_string == '超过续借次数, 不能续借!':
                status[i.string] = 'This book can not be renewed!'
            else:
                status[i.string] = 'Renew successfully'
        return status
                
