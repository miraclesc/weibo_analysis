import numpy as np
import pandas as pd
import os
import time
import math
import re
import datetime
from dateutil.parser import parse
from collections import Counter
from wordcloud import WordCloud,ImageColorGenerator
import jieba
import jieba.analyse
import warnings
warnings.filterwarnings('ignore')

#可以去除内容中#主题#，[表情], url等固定格式
def remove_format(content,*model):
    remove = []
    for model_i in model:
        remove += model_i.findall(str(content))
    for i in remove:
        content = content.replace(i,'')
    return content

#判断是否有相应的词
def exist_white(content,*words):
    if str(content) == '':
        return 0
    wordList = []
    for word in words:
        wordList += word
    flag = 0
    for name in wordList:
        if name in str(content):
            flag = 1
            break
    return flag

#判断是否有黑名单的主题词
def exist_black(content):
    flag = 0
    topic = pattern_topic.findall(content)
    if topic != []:
        for topic_temp in topic:
            if topic_temp in blackList:
                flag = 1
                break
    return flag

#判断日期格式是否为有效日期
def is_valid_date(strdate):
    try:
        time.strptime(strdate, "%Y/%m/%d %H:%M")
        return True
    except:
        return False

#是否在规定的时间范围 4月1日至6月30日
def interval_date(strtime):
    if strtime.year != 2018 or strtime.month < 4 or strtime.month > 6:
        return False
    else: True

#昵称是否符合规范
def name_fail(user_name):
    #合法名称不应该包含的字符
    if '#' in user_name or '/' in user_name or ' ' in user_name:
        return True
    #昵称长度是否符合规范
    length = len(user_name)
    utf8_length = len(user_name.encode('utf-8'))
    length = (utf8_length - length)/2 + length
    if length < 4 or length > 30:
        return True
    else:
        return False
#是否是机器用户的一般形式的名称（用户123456890, 某某某_xyz）
def machine_name(user_name):
    if user_name in re.compile(r'(用户[\da-zA-Z]{9,})').findall(user_name):
        return True
    elif pattern_name.findall(user_name) != [] and  pattern_name.findall(user_name)[0] == user_name:
        return True
    else:
        return False

#大写都转为小写，去除文字两端空格等符号,去除过多空格等
def up_to_low(line):
    line = line.lower()
    line = line.strip(' ·-?。"\'\n')
    line = line.replace('  ','')
    line = line.replace('??','?')
    return line

#计算微博是否重复时截取的固定长度
def cut_pure(pure):
    if len(pure) <= 10:
        length = len(pure)
    elif len(pure) >= 100:
        length = 100
    else:
        length = int(len(pure)/10)*10
    pure = pure[:length]
    return pure

#第一次判断原微博是否为无意义微博
def class_original(weibo, user, *city):
    #1为正常微博，2为打榜微博，0为与主题不相关微博，3为待定微博
    #官方微博账号发布和参赛选手嘉宾发布
    if user in star or user in official:
        return 1
    #已经确认的水军用户
    if user in blackuser:
        return 0

    if '#创造101#' in weibo and len(pattern_topic.findall(weibo))<=2:    
        content = remove_format(weibo,pattern_topic)
        #去除类似 “评论个 #创造101#“ 这样的微博
        content = re.sub('[\.\！\/_()><$%^*+!\"\']+|[\[\]《》【】！？♀“”+—#。、~￥……&（） ?]+|[\d]+','',content)
        content = ''.join([seg for seg in content if seg not in stopwords])
        if content == '':
            return 0    
    
    weibo_nospace = weibo.replace(' ','')
    
    #去除有其他不相关主题且与原主题毫无关联的微博
    if exist_black(weibo_nospace):
        content = remove_format(weibo,pattern_url,pattern_topic)
        if exist_white(content,whiteList_high):
            return 1
        else: return 0
    
    #将有打榜关键词的微博定义为活动微博
    if exist_white(weibo_nospace, callList) and not exist_black(weibo_nospace):
        return 2
    if exist_white(weibo_nospace, callList2) and pattern_url.findall(weibo) != []:
        return 2
    
    #含有常见广告不相关词的为水军
    weibo_format = remove_format(weibo,pattern_topic,pattern_facial,pattern_url)
    if exist_white(weibo_format, adword):
    	return 0
    
    #水军高发城市或者机器名称用户会提前进入筛选
    if (city and city[0] in blackcity) or machine_name(user):
        flag = 0
        if '#创造101' in weibo:
            weibo = weibo.replace('#创造101','')
            flag = 1
        if '#火箭少女101' in weibo:
            weibo = weibo.replace('#火箭少女101','')[2:]
            flag = 1
        if flag:
            if exist_white(weibo,whiteList_high,whiteList,shortword):
                return 3
            else:
                return 0
    #待定微博
    return 3

#提取转发微博的实际内容，上一层被转发者，属于几级转发
def deal_repost(content):
    content_list = content.split('//@')
    level = len(content_list)
    weibo_content = content_list[0]
    weibo_repost_user = ''
    if level != 1:
        repost_user = re.compile(r'([^:|：]+)').findall(content_list[1])
        if repost_user != []:
            weibo_repost_user = repost_user[0].strip()
            if name_fail(weibo_repost_user):
                weibo_repost_user = ''    
    
    #普通转发微博
    weibo_content = weibo_content.strip(' ') 
    #去除内容中 主题 表情 网站 无意义数字字母 符号
    weibo_content = remove_format(weibo_content,pattern_topic,pattern_facial,pattern_url,pattern_nothing) 
    weibo_content_nosymbol = re.sub('[\.\！\/_()><$%^*+!\"\']+|[\[\]《》【】！？♀“”+—#，。、~￥……&（）\s ?]+','',weibo_content)
    if weibo_content_nosymbol == '转发微博' or weibo_content_nosymbol == '轉發微博' or weibo_content_nosymbol == '':
        return '', weibo_repost_user, level 
    else:
        return content_list[0], weibo_repost_user, level
    
#第二次判断原微博是否为无意义微博
def class_original2(weibo,kind):
    weibo_format = remove_format(weibo,pattern_topic,pattern_facial,pattern_url)
    if not exist_white(weibo_format,whiteList_high,whiteList) and len(weibo_format) > 50:
        return 0
    flag = 0
    if '#创造101' in weibo:
        weibo_format = weibo.replace('#创造101','')
        flag = 1
    if '#火箭少女101' in weibo:
        weibo_format = weibo.replace('#火箭少女101','')[2:]
        flag = 1
    if flag and len(pattern_topic.findall(weibo))==1:
        if kind == 1:
            if exist_white(weibo_format,whiteList_high,whiteList,shortword): return 1
            else: return 0
        elif kind == 2:
            if exist_white(weibo_format,whiteList_high,whiteList): return 1
            else: return 0
        elif kind == 3:
            if exist_white(weibo_format,whiteList_high): return 1
            else: return 0
    return 1


#数据预处理第一步，去除格式不正确的数据，分离原创和转发，标记原创中部分与主题无关的水军，将转发无意义的内容设置为空内容，按日期分别存储
def pre_first(input_file, output_file):
    date = []
    createVar = locals()
    target_file = os.listdir(input_file)
    num_all = 0
    num_regular = 0
    index = 0
    for file in target_file:
        begin = time.time()
        with open(input_file + '/' + file, 'r', encoding = 'gb18030') as data:
            date_temp = []
            old_title = data.readline()
            while True:
                line = data.readline()
                #每读完一个文件都关闭所有打开的文件，避免内存溢出
                if line == '':
                    for day in date_temp:
                        createVar[day + '_file'].close()
                    break

                num_all+=1
                line = line.split(',')
                if len(line) != 18:
                    continue

                if line[0] == '原创':
                    #判断数据是否符合规范，是否是有效日期，有效用户名，有效发布城市
                    if is_valid_date(line[8]):
                        weibo_time = parse(line[8])
                    else: continue
                    if name_fail(line[3]): continue
                    if line[17] == '\n': line[17] = line[16] + line[17]
                    if pattern_nocity.findall(line[17]) != []: continue

                    line[1] = up_to_low(line[1])
                    #是否是价值微博 '0'为无价值
                    sort = str(class_original(line[1],line[3],line[17].strip()))
                    if interval_date(weibo_time) == False: sort = '0'
                    #微博内容,MID,用户昵称,用户性别,发布时间,识别分类,发布省份,发布城市
                    weibo_temp = [line[1],line[2],line[3],line[5],line[8],sort,line[16],line[17]]
                    weibo_day = str(weibo_time.year) + '_' + str(weibo_time.month) + '_' + str(weibo_time.day) + '_original'
                
                elif line[0] == '转发':
                    if is_valid_date(line[15]):
                        weibo_time = parse(line[15])
                    else: continue
                    if name_fail(line[3]) or name_fail(line[11]): continue
                    if line[17] == '\n': line[17] = line[16] + line[17]
                    if pattern_nocity.findall(line[17]) != []: continue

                    #纯内容，上级转发者，转发层级
                    content, reposted_user, level = deal_repost(line[9])
                    #无上一级用户或上一级用户名称可能识别不出来
                    if reposted_user == '': reposted_user = line[3]
                    content, line[9], line[1]= up_to_low(content),up_to_low(line[9]),up_to_low(line[1])
                    #按原创的内容来分类
                    sort = str(class_original(line[1],line[3]))
                    if interval_date(weibo_time) == False: sort = '0'
                    if reposted_user == line[11] or line[3] == line[11]: sort = '0'

                    #纯微博内容,MID,昵称,性别,发布时间,全部内容,原创mid,上级用户,原创用户,转发层级,原创识别分类,发布省份,发布城市
                    weibo_temp = [content,line[10],line[11],line[13],line[15],line[9]+line[1],line[2],reposted_user,line[3],str(level)+'级转发',sort,line[16],line[17]]
                    weibo_day = str(weibo_time.year) + '_' + str(weibo_time.month) + '_' + str(weibo_time.day) + '_repost'                
                
                else: continue
                
                #按日期分文件存储    
                if weibo_day not in date:
                    date.append(weibo_day)
                if weibo_day not in date_temp:
                    date_temp.append(weibo_day)
                    createVar[weibo_day + '_file'] = open(output_file+'/'+weibo_day+'.csv','a',encoding = 'gb18030')
                createVar[weibo_day + '_file'].writelines(','.join(weibo_temp))
                num_regular += 1
        index += 1
        print('完成第%d个文件耗时%f秒'%(index,time.time()-begin))
    print('原始文件一共%d条'%num_all)
    print('符合格式规范的数据一共%d条'%num_regular)
    return date


#数据预处理第二步，从转发内容中提取一些原创项目中可能没有的原创内容,分发到各个相应日期中
def pre_second(date,input_file,output_file):
    target_file = os.listdir(input_file)
    title = ['原微博内容','原微博伪MID（MD5加密）','原微博用户昵称','原微博用户性别','原微博发布时间','原微博用户省份','原微博用户城市']
    original_df = pd.DataFrame(columns= title)
    
    #提取原创微博
    for file_temp in target_file:
        temp = pd.read_csv(input_file + '/' + file_temp, encoding = 'gb18030')
        temp = temp[temp['是否转发'] == '转发']
        temp_result = temp.drop_duplicates(subset=['原微博伪MID（MD5加密）','原微博发布时间'], keep='first', inplace=False)
        temp_result = temp_result[title]
        original_df = original_df.append(temp_result,ignore_index=True)
        original_df = original_df.drop_duplicates(subset=['原微博伪MID（MD5加密）','原微博发布时间'], keep='first', inplace=False)
    original_df.to_csv('original.csv',index=None)

    #分发原创到相应日期
    with open('original.csv','r',encoding='utf-8') as f:
        old_title = f.readline()
        while True:
            line = f.readline()
            if line == '':
                break
            #与预处理第一步判断方式相同
            line = line.split(',')
            if len(line) != 7:
                continue
            if is_valid_date(line[4]):
                weibo_time = parse(line[4])
                if interval_date(weibo_time) == False: continue
            else:
                continue
            if name_fail(line[2]): continue
            if line[6] == '' or line[6] == '\n':
                line[6] = line[5] + line[6]
            if '\n' not in line[6]:
                line[6] = line[6] + '\n'
            if pattern_nocity.findall(line[6]) != []: continue

            line[0] = up_to_low(line[0])
            sort = str(class_original(line[0],line[2]))
            weibo_day = str(weibo_time.year) + '_' + str(weibo_time.month) + '_' + str(weibo_time.day) + '_original'
            #微博内容,MID,用户昵称,用户性别,发布时间,识别分类,发布省份,发布城市
            weibo_temp = [line[0],line[1],line[2],line[3],line[4],sort,line[5],line[6]]
            if weibo_day not in date:
                date.append(weibo_day)
            f_original = open(output_file+'/'+weibo_day+'.csv','a',encoding = 'gb18030')
            f_original.writelines(','.join(weibo_temp))
            f_original.close()
    os.remove('original.csv')


#预处理第三步，内容识别，将之前标记识别分类分开；行为识别，去除一个用户一天内多次发布相似内容
def pre_third(input_file,output_file):
    target_file = os.listdir(input_file)
    index = 0
    num_repost_1 = 0
    num_repost_2 = 0
    num_original_1 = 0
    num_original_2 = 0
    for file_temp in target_file:
        begin = time.time()
        type_file = file_temp.split('.')[0].split('_')[-1]
        if type_file == 'repost':
            title = ['微博内容','MID','用户昵称','用户性别','发布时间','全部内容','原创微博id','上级用户','原创用户','转发层级','识别分类','发布省份','发布城市']
        else:
            title = ['微博内容','MID','用户昵称','用户性别','发布时间','识别分类','发布省份','发布城市','微博纯文字内容','文字不含主题']
        temp_list = []
        #以open方式打开，为了避免一些不可预见的错误
        with open(input_file + '/' + file_temp,'r',encoding = 'gb18030') as temp:
            while True:
                line = temp.readline()
                if line == '':
                    break
                line = line.split(',')
                line[-1] = line[-1].strip()
                #原创中微博纯文字内容
                if type_file == 'original':
                    pure = remove_format(line[0],pattern_facial,pattern_url,pattern_nothing)
                    pure = re.sub('[\.\！\/_()><$%^*+!\"\']+|[\[\]《》【】！？♀“”+—。，、@~￥……&（） ?\d]+|[a-zA-Z]','',pure)
                    #部分微博开头一样，结尾用不同的文字结尾
                    pure = cut_pure(pure)
                    line.append(pure)
                    line.append(remove_format(pure,pattern_topic))
                temp_list.append(line)
        temp_df = pd.DataFrame(temp_list,columns=title)
        temp_df = temp_df.drop_duplicates(subset=['MID'], keep='last', inplace=False)
        temp_df.to_csv(input_file + '/' + file_temp,columns=['微博内容','用户昵称','用户性别','发布时间','发布省份','发布城市'],index=None)
        
        #对于转发微博，同一用户转发某一特定用户的内容，疑似水军或故意刷转发量只保留一条
        #对于原创微博，同一用户同一天原创多条类型或者相同的微博，恶意刷数量只保留一条
        if type_file == 'repost':
            temp_worth = temp_df[temp_df['识别分类']!='0']
            num_repost_1 += len(temp_df) - len(temp_worth)
            result=temp_worth.drop_duplicates(subset=['用户昵称','上级用户','原创用户','转发层级','原创微博id','发布城市'], keep='first',inplace=False)
            num_repost_2 += len(temp_worth) - len(result)
            del result['识别分类']
        
        else:
            temp_worth = temp_df[temp_df['识别分类']!='0']
            num_original_1 += len(temp_df) - len(temp_worth)
            result_all = temp_worth.drop_duplicates(subset=['文字不含主题','用户昵称'], keep='first', inplace=False)
            del result_all['文字不含主题']
            num_original_2 += len(temp_worth) - len(result_all)
            result = result_all[result_all['识别分类'] != '2']
            
            activity = result_all[result_all['识别分类'] == '2']
            del activity['识别分类']
            del activity['微博纯文字内容']
            activity.to_csv(output_file + '/'+'_'.join(file_temp.split('/')[-1].split('_')[:3])+'_activity.csv',index=None,encoding = 'gb18030')
        
        result.to_csv(output_file + '/'+file_temp.split('/')[-1],index=None,encoding = 'gb18030')
        index += 1
        print('完成第%d个文件耗时%f秒'%(index,time.time()-begin))
    print('原创中筛选无意义%d条，原创去重筛选掉数据%d条'%(num_original_1,num_original_2))
    print('转发中筛选无意义%d条，转发去重筛选掉数据%d条'%(num_repost_1,num_repost_2))


#统计用户特征
def count_group(df):
    return len(df)
def count_sex(df):
    sex = list(df['用户性别'].drop_duplicates(keep='first'))
    if '男' in sex:
        return '男'
    elif '女' in sex:
        return '女'
    else: return ''
def count_fans(df):
    fans_name = list(df['用户昵称'].drop_duplicates(keep='first'))
    return fans_name

#向字典添加项和值,原创，转发，参与活动，被直接转发(不包括间接转发)，用户原创被转发总量，用户总体被转发总量（包括原创被转发，转发微博被接着转发）等
def add_dict(dict_temp, dict_result, index):
    for key,item in dict_temp.items():
        if key not in dict_result:
            dict_result[key] = [0,0,0,0,0,0]
        dict_result[key][index] += item
    return dict_result
def add_num(dict_temp, dict_result):
    for key, item in dict_temp.items():
        if key not in dict_result:
            dict_result[key] = item
        else:
            dict_result[key] += item
    return dict_result

#日期排序
def get_timestamp(date,style):
    if style == 1:
        return datetime.datetime.strptime(date,'%Y/%m/%d').timestamp()
    elif style == 2:
        return datetime.datetime.strptime(date,'%Y-%m-%d').timestamp()
    else:
        return datetime.datetime.strptime(date,'%Y/%m/%d %H:%M').timestamp()

#预处理第四步，计算用户特征原创，转发，被转发数量等特征
def pre_fourth(input_file):
    target_file = os.listdir(input_file)
    #user为用户原创数等，user_date为用户活跃日期，user_active为用户活跃天数，user_gender为用户性别，user_fans为用户粉丝
    user = {}
    user_date = {}
    user_active = {}
    user_gender = {}
    user_fans = {}
    weibo_all = {}
    index = 0
    for file_temp in target_file:
        begin = time.time()
        type_file = file_temp.split('.')[0].split('_')[-1]
        data = pd.read_csv(input_file + '/' + file_temp,encoding = 'gb18030')
        date = '/'.join(file_temp.split('_')[:3])
        
        #主动，即用户主动原创数量，主动转发数量
        user_initiative= dict(data.groupby('用户昵称').apply(count_group))
        #计算用户原创数，转发数，活动数
        if type_file == 'original':
            user = add_dict(user_initiative, user, 0)
        elif type_file == 'repost':
            user = add_dict(user_initiative, user, 1)   
        else:
            user = add_dict(user_initiative, user, 2)
        
        #添加用户性别
        user_sex = dict(data.groupby('用户昵称').apply(count_sex))
        for key,item in user_sex.items():
            if key not in user_gender:
                user_gender[key] = item
            else:
                if user_gender[key] == '' and item != '':
                    user_gender[key] = item
                    
        #添加用户活跃的日期
        for key in user_initiative.keys():
            if key not in user_date:
                user_date[key] = []
            if date not in user_date[key]:
                user_date[key].append(date)
        
        #被动，即用户微博被转发数量
        if type_file == 'repost':
            #用户直接转发，原创总转发量
            user_passive1 = dict(data.groupby('上级用户').apply(count_group))
            user_passive2 = dict(data.groupby('原创用户').apply(count_group))
            user = add_dict(user_passive1,user,3)
            user = add_dict(user_passive2,user,4)
            #用户的粉丝
            user_fans_temp = dict(data.groupby('上级用户').apply(count_fans))
            user_fans = add_num(user_fans_temp,user_fans)
            
            #所有微博总转发量，包括直接转发和间接转发
            data_repost1 = data[data['上级用户'] != data['原创用户']]
            data_repost2 = data[data['上级用户'] == data['原创用户']]
            user_passive3 = dict(data_repost1.groupby('上级用户').apply(count_group))
            user_passive4 = dict(data_repost1.groupby('原创用户').apply(count_group))
            user_passive5 = dict(data_repost2.groupby('原创用户').apply(count_group))
            user = add_dict(user_passive3,user,5)
            user = add_dict(user_passive4,user,5)
            user = add_dict(user_passive5,user,5)           
            #统计微博总转发量
            weibo_all_temp = dict(data.groupby('原创微博id').apply(count_group))
            weibo_all = add_num(weibo_all_temp, weibo_all)
        index += 1
        print('完成第%d个文件耗时%f秒'%(index,time.time()-begin))
    
    #计算活跃天数，将活跃日期排序
    for key,item in user_date.items():
        user_active[key] = [len(item)]
        user_date[key] = ','.join(sorted(item, key=lambda date:get_timestamp(date,1)))

    #用户属性整体
    user_all = {}
    for key,item in user_active.items():
        try:
            fans_num = len(list(set(user_fans[key])))
        except:
            fans_num = 0
        user_all[key] = user[key] + item + [user_date[key]] + [user_gender[key]] + [fans_num]
    
    user_df = pd.DataFrame(user_all).T
    user_df.columns = ['用户原创量','用户转发量','参与活动量','用户所有微博被直接转发量','用户原创微博总体被转发量(包括间接转发)','用户所有微博总体被转发量(包括间接转发)','活跃天数','活跃日期','用户性别','用户粉丝数']
    
    user_df['参与日的日均参与'] = (user_df['用户原创量'] + user_df['用户转发量'] + user_df['参与活动量']) / user_df['活跃天数']
    user_df['整体时段日均参与'] = (user_df['用户原创量'] + user_df['用户转发量'] + user_df['参与活动量']) / 91
    user_df['时间参与率'] = user_df['活跃天数'] / 91
    user_df['时间参与率']= user_df['时间参与率'].apply(lambda x: '%.2f%%' % (x*100))

    #计算直接转发率，即该条微博直接从他这里转发的比率，越高越说明传播没有层级
    rate = []
    direct_repost = list(user_df['用户所有微博被直接转发量'])
    all_repost = list(user_df['用户所有微博总体被转发量(包括间接转发)'])
    for repost1,repost2 in zip(direct_repost,all_repost):
        if repost2 == 0:
            rate.append(0)
        else:
            rate.append(repost1/repost2)
    user_df['直接转发率'] = rate
    user_df['直接转发率'] = user_df['直接转发率'].apply(lambda x: '%.2f%%' % (x*100))
    
    P1 = max(list(user_df['用户原创量']+user_df['用户原创量']+user_df['参与活动量']))
    P2 = max(list(user_df['用户所有微博总体被转发量(包括间接转发)']))
    P3 = max(list(user_df['用户粉丝数']))
    #该计算方法待定
    user_df['用户影响力'] = ((user_df['用户原创量']*0.5+user_df['用户转发量']*0.25+user_df['参与活动量']*0.25)/P1*0.3 + user_df['用户所有微博总体被转发量(包括间接转发)']/P2*0.4 + user_df['用户粉丝数']/P3*0.3)*100
    
    user_df = user_df.sort_values(by=['用户影响力'],ascending = False)
    print('处理后一共有%d位用户'%len(user_df))
    user_df.to_csv('result/user.csv')
    
    #user_repost字典用于计算下一步
    user_repost = user_df[user_df['用户原创微博总体被转发量(包括间接转发)']>0]
    user_repost = user_repost[['用户原创微博总体被转发量(包括间接转发)','活跃日期']].T.to_dict('list')
    
    #用户计算该用户一共转发了多少条微博，原创多少条微博，参与多少次活动
    user_original = user_df[user_df['用户原创量']>0]
    user_original = user_original[['用户原创量','活跃天数']].T.to_dict('list')
    user_repost_num = user_df[user_df['用户转发量']>0]
    user_repost_num = user_repost_num[['用户转发量','活跃天数','活跃日期']].T.to_dict('list')    
    user_active = user_df[user_df['参与活动量']>0]
    user_active = user_active[['参与活动量','活跃天数','活跃日期']].T.to_dict('list')   
    user_df.to_csv('result/全部用户信息.csv')
    
    return user_repost,user_repost_num,user_original,user_active,weibo_all


#向原创中添加转发量特征,统计总体转发量最高的前1000条微博
def pre_fifth(input_file,weibo_all,user_repost,user_repost_num,user_original,user_active,check=True):
	#活跃单一较可疑
    user_df = pd.read_csv('result/user.csv',index_col=0)
    user_df = user_df[user_df['用户原创量'] > 0]
    user_df = user_df[user_df['用户转发量'] == 0]
    user_df = user_df[user_df['参与活动量'] == 0]
    user_df = user_df[user_df['用户粉丝数'] <= 1]
    user_sus = list(user_df.index)
    user_all_name = list(user_repost.keys())
    num_original = 0
    num_repost = 0
    
    #统计转发量最高的前1000条微博
    weibo_df = pd.DataFrame([weibo_all]).T
    weibo_df.columns = ['总体转发量']
    weibo_df = weibo_df.sort_values(by='总体转发量',ascending = False)[:1000]
    weibo_df.to_csv('result/weibo_top1000_mid.csv')
    weibo_top1000 = list(weibo_df.index)
    weibo_top1000_num = list(weibo_df['总体转发量'])
    weibo_title = ['微博内容','用户昵称','用户性别','发布时间','发布省份','发布城市']
    weibo_top = pd.DataFrame(columns=weibo_title)
    
    #order为了统计排序
    order = []
    index = 0
    target_file = os.listdir(input_file)
    for file_temp in target_file:
        begin = time.time()
        type_file = file_temp.split('.')[0].split('_')[-1]
        data = pd.read_csv(input_file + '/' + file_temp,encoding = 'gb18030')
        date = '/'.join(file_temp.split('.')[0].split('_')[:-1])
        if type_file == 'original':
            #该条原创微博总体转发量,该用户原创微博总体转发量等
            repost_all = []
            user_repost_all = []
            original_all = []
            active_day = []
            data_mid = list(data['MID'])
            data_user = list(data['用户昵称'])
            if check == False:
                #计算原创总体转发量，只与原创微博id相关，避免直接搜索data_mid造成时间浪费
                for user,mid in zip(data_user, data_mid):
                    if user in user_all_name:
                        if date in user_repost[user][1].split(','):
                            try:
                                repost_all.append(weibo_all[mid])
                            except:
                                repost_all.append(0)
                            if mid in weibo_top1000:
                                order.append(weibo_top1000.index(mid) + 1)
                                temp = data[data['MID'] == mid]
                                temp = temp[weibo_title]
                                weibo_top = weibo_top.append(temp,ignore_index=True)
                        else: repost_all.append(0)
                        user_repost_all.append(user_repost[user][0])
                    else:
                        repost_all.append(0)
                        user_repost_all.append(0)
                    try:
                        original_all.append(user_original[user][0])
                        active_day.append(user_original[user][1])
                    except:
                        original_all.append(0)
                        active_day.append(0)
                
                data['该条微博总体转发量'] = repost_all
                data['该用户原创微博数'] = original_all
                data['该用户原创微博总体转发量'] = user_repost_all
                data['该用户活跃天数'] = active_day
                data = data[data['该用户原创微博数'] != 0]
            
            if check and '识别分类' in list(data.columns):
                for user in data_user:
                    if user in user_all_name:
                        user_repost_all.append(user_repost[user][0])
                    else:
                        user_repost_all.append(0)
                data['该用户原创微博总体转发量'] = user_repost_all
                len_before = len(data)
                data_star = data[data['识别分类'] == 1]
                data_normal = data[data['识别分类'] != 1]
                data_repost_0 = data_normal[data_normal['该用户原创微博总体转发量'] == 0]
                data_repost_0 = data_repost_0.drop_duplicates(subset=['微博纯文字内容','发布城市'], keep='first',inplace=False)
                data_repost_1 = data_normal[data_normal['该用户原创微博总体转发量'] != 0]
                data_normal = pd.concat([data_repost_1,data_repost_0],axis=0)
                repost_all_this = list(data_normal['该用户原创微博总体转发量'])
                city_this = list(data_normal['发布城市'])
                user_this = list(data_normal['用户昵称'])
                weibo_content = list(data_normal['微博内容'])
                sort_new = []
                for i in range(len(data_normal)):
                    if repost_all_this[i] == 0:
                        try:
                            if machine_name(user_this[i]) or (user_this[i] in user_sus and city_this[i] in blackcity):
                                sort_new.append(str(class_original2(str(weibo_content[i]),3)))
                            elif city_this[i] in blackcity:
                                sort_new.append(str(class_original2(str(weibo_content[i]),2))) 
                            else:
                                sort_new.append(str(class_original2(str(weibo_content[i]),1)))
                        except:
                            sort_new.append('0')
                    else:
                        sort_new.append('1')
                data_normal['新分类'] = sort_new
                if len(data_normal) > 0:
                    data_normal = data_normal[data_normal['新分类'] == '1']
                    del data_normal['新分类']
                data = pd.concat([data_star,data_normal], axis=0)
                del data['微博纯文字内容']
                del data['识别分类']
                del data['该用户原创微博总体转发量']
                print('原创筛选掉微博%d条'%(len_before-len(data)))
                num_original += len_before-len(data)
            data.to_csv(input_file + '/' + file_temp,index=None,encoding = 'gb18030')
        
        elif type_file == 'repost':
            repost_num = []
            active_day = []
            active_date = []
            data_user = list(data['用户昵称'])
            for user in data_user:
                try:
                    repost_num.append(user_repost_num[user][0])
                    active_day.append(user_repost_num[user][1])
                    active_date.append(user_repost_num[user][2])
                except:
                    repost_num.append(0)
                    active_day.append(0)
                    active_date.append(0)
            
            data['该用户总转发量'] = repost_num
            data['该用户活跃天数'] = active_day
            data['用户活跃日期'] = active_date
            data = data[data['该用户总转发量'] != 0]
            if check:
                #在整个过程行为完全一样，十分可疑
                len_before = len(data)
                data = data.drop_duplicates(subset=['微博内容','上级用户','原创用户','原创微博id','发布城市','该用户总转发量','该用户活跃天数','用户活跃日期'], keep='first',inplace=False)
                print('转发筛选掉微博%d条'%(len_before-len(data)))
                num_repost += len_before-len(data)
            del data['用户活跃日期']
            data.to_csv(input_file + '/' + file_temp, index=None, encoding = 'gb18030')
        
        else:
            data_user = list(data['用户昵称'])
            data_mid = list(data['MID'])
            if check == False:
                active_num = []
                active_day = []
                for user in data_user:
                    try:
                        active_num.append(user_active[user][0])
                        active_day.append(user_active[user][1])
                    except:
                        active_num.append(0)
                        active_day.append(0)
                data['该用户总活动量'] = active_num
                data['该用户活跃天数'] = active_day
            
            else:
                repost_maybe = []
                for user,mid in zip(data_user,data_mid):
                    if user in user_all_name:
                        try:
                            repost_maybe.append(weibo_all[mid])
                        except:
                            repost_maybe.append(0)
                    else:
                        repost_maybe.append(0)
                len_before = len(data)
                data['该条微博总体转发量'] = repost_maybe
                data_active = data[data['该条微博总体转发量']!=0]
                #如果一条活动微博有转发量，则将其转化为原创
                if len(data_active) > 0:
                    file_name = input_file + '/' +'_'.join(file_temp.split('.')[0].split('_')[:-1])+'_original.csv'
                    data_original = pd.read_csv(file_name,encoding = 'gb18030')
                    del data_active['该条微博总体转发量']
                    data_original = pd.concat([data_original,data_active],axis=0)
                    data_original.to_csv(file_name,index=None,encoding = 'gb18030')
                data = data[data['该条微博总体转发量']==0]
                del data['该条微博总体转发量']
                print('活动中转化微博%d条'%(len(data_active)))
            data.to_csv(input_file + '/' + file_temp,index=None,encoding = 'gb18030')
            
        index += 1
        print('完成第%d个文件耗时%f秒'%(index,time.time()-begin))
    if check == False:
        weibo_top['排名'] = order
        weibo_top = weibo_top.sort_values(by='排名')
        weibo_top['转发量'] = weibo_top1000_num[:len(weibo_top)]
        weibo_top.to_csv('result/微博转发量排名.csv',index=None)
    else:
        print('该过程剔除原创%d条，转发%d条'%(num_original,num_repost))


#时间排序
def sort_date(df):
    date_list = list(df['发布时间'])
    date_list2 = sorted(date_list, key=lambda date:get_timestamp(date,3))
    sort_list = []
    for date in date_list:
        sort_list.append(date_list2.index(date))
    df['排序顺序'] = sort_list
    df = df.sort_values(by = '排序顺序')
    del df['排序顺序']
    return df

#一个日期下的原始数据原创，原始数据转发，原创数量，转发数量，活动数量
def add_date(key,item, dict_result, index):
    if key not in dict_result:
        dict_result[key] = [0,0,0,0,0]
    dict_result[key][index] += item
    return dict_result

#重命名，移动文件位置, 释放文件，按日期计算各文件数量
def pre_six(input_file1, input_file2, output_file):
    date_weibo_num = {}
    target_file1 = os.listdir(input_file1)
    for file_temp in target_file1:
        type_file = file_temp.split('.')[0].split('_')[-1]
        date_temp = '-'.join(file_temp.split('_')[:-1])
        data = pd.read_csv(input_file1 + '/' + file_temp)
        if type_file == 'original':
            date_weibo_num = add_date(date_temp,len(data),date_weibo_num,0)
        else:
            date_weibo_num = add_date(date_temp,len(data),date_weibo_num,1)
        os.remove(input_file1 + '/' + file_temp)
    
    target_file2 = os.listdir(input_file2)
    for file_temp in target_file2:
        type_file = file_temp.split('.')[0].split('_')[-1]
        data = pd.read_csv(input_file2 + '/' + file_temp,encoding = 'gb18030')
        file_date = '-'.join(file_temp.split('_')[:-1])
        if type_file == 'original':
            data = sort_date(data)
            original_columns = ['微博内容','MID','用户昵称','用户性别','发布时间','发布省份','发布城市','该条微博总体转发量','该用户原创微博数','该用户原创微博总体转发量','该用户活跃天数']
            data = pd.DataFrame(data,columns=original_columns)
            data.to_csv(output_file+'/original/'+file_date+'.csv', index = None)
            date_weibo_num = add_date(file_date,len(data),date_weibo_num,2)
        elif type_file == 'repost':    
            data.to_csv(output_file+'/repost/'+file_date+'.csv', index = None)
            date_weibo_num = add_date(file_date,len(data),date_weibo_num,3)
        else:
            data.to_csv(output_file+'/active/'+file_date+'.csv', index = None)
            date_weibo_num = add_date(file_date,len(data),date_weibo_num,4)
        os.remove(input_file2 + '/' + file_temp)
    
    date = sorted(list(date_weibo_num.keys()), key=lambda date:get_timestamp(date,2))
    date_weibo = pd.DataFrame(date_weibo_num)
    sum_num = list(date_weibo.sum(axis=1))
    date_weibo = date_weibo[date]
    date_weibo['总和'] = sum_num
    date_weibo = date_weibo.T
    date_weibo.columns = ['原数据原创','原数据转发','原创','转发','活动']
    date_weibo['水军量'] = date_weibo['原数据原创']+date_weibo['原数据转发']-date_weibo['原创']-date_weibo['转发']-date_weibo['活动']
    date_weibo.to_csv('result/date_weibo.csv')

#附加功能1：删除某些固定用户的所有原创微博
def del_user(user_list):
    user = pd.read_csv('result/user.csv',index_col=0)
    all_user = list(user.index)
    user_yhyc = user['用户原创量']
    sort = []
    for i in range(len(all_user)):
        if user_yhyc[i] > 0:
            if all_user[i] in user_list:
                sort.append(0)
            else:
                sort.append(1)
        else:
            sort.append(1)
    user['判断'] = sort
    user_use = user[user['判断'] == 1]
    del user_use['判断']
    user_use.to_csv('result/user.csv')

    user_useless = user[user['判断'] == 0]
    user_useless_date = list(user_useless['活跃日期'])
    user_useless_name = list(user_useless.index)

    input_file = 'result/original'
    target_file = os.listdir(input_file)
    for file in target_file:
        date = '/'.join(file.split('.')[0].split('-'))
        black_user_name_temp = []
        for i in range(len(user_useless_date)):
            if date in user_useless_date[i]:
                black_user_name_temp.append(user_useless_name[i])

        data = pd.read_csv(input_file+ '/'+file)
        kind = []
        data_user = list(data['用户昵称'])
        for user_name in data_user:
            if user_name in black_user_name_temp:
                kind.append(0)
            else: kind.append(1)
        data['判断'] = kind
        data = data[data['判断']==1]
        del data['判断']
        data.to_csv(input_file + '/' + file,index=None)

#附加功能2：将某些含特定关键字微博从原创转化为活动
def transfer(call_list):
    user = pd.read_csv('result/user.csv',index_col=0)
    input_file = 'result/original'
    target_file = os.listdir(input_file)
    user_transfer = {}
    for file in target_file:
        data = pd.read_csv(input_file + '/' + file)
        sort_temp = []
        content_all = data['微博内容']
        user_all = data['用户昵称']
        repost_all = data['该条微博总体转发量']
        for i in range(len(data)):
            if repost_all[i] > 0:
                sort_temp.append(1)
            else:
                if exist_white(content_all[i],call_list) == 1:
                    sort_temp.append(0)
                    try:
                        user_transfer[user_all[i]]+=1
                    except:
                        user_transfer[user_all[i]]=1
                else:sort_temp.append(1)
        data['非活动'] = sort_temp
        active_temp = data[data['非活动'] == 0]
        if len(active_temp)>0:
            data = data[data['非活动'] == 1]
            del data['非活动']
            data.to_csv(input_file + '/' + file,index=None)
            active = pd.read_csv('result/active/' + file)
            user_this = active_temp['用户昵称']
            active_num = []
            for user_temp in user_this:
                #这里活动量会有一定误差，不过是非重要参数，为了减少计算量省略
                active_num.append(user_use.loc[user_temp]['参与活动量']+1)
            active_temp['该用户总活动量'] = active_num
            active_temp = pd.DataFrame(active_temp,columns=['微博内容','MID','用户昵称','用户性别','发布时间','发布省份','发布城市','该用户总活动量','该用户活跃天数'])
            active = pd.concat([active,active_temp],axis=0)
            active.to_csv('result/active/' + file,index=None)
    for item, key in user_transfer.items():
        user.loc[item,'用户原创量']-=key
        user.loc[item,'参与活动量']+=key
    user.to_csv('result/user.csv')

#如果使用附加功能需要重新计算日期下微博量
def cal_date(input_file,columns_name):
    date_weibo = pd.read_csv('result/date_weibo.csv',index_col=0)
    target_file = os.listdir(input_file)
    date_dict = {}
    for file in target_file:
        data = pd.read_csv(input_file+'/' + file)
        date = file.split('.')[0]
        date_dict[date] = len(data)
    date_df = pd.DataFrame([date_dict])
    date_df['总和'] = list(date_df.sum(axis=1))
    date_df = date_df.T
    date_df.columns = [columns_name]
    del date_weibo[columns_name]
    date_weibo = date_weibo.join(date_df)
    date_weibo['水军量'] = date_weibo['原数据原创']+date_weibo['原数据转发']-date_weibo['原创']-date_weibo['转发']-date_weibo['活动']
    date_weibo = pd.DataFrame(date_weibo,columns=['原数据原创','原数据转发','原创','转发','活动','水军量'])
    date_weibo.to_csv('result/date_weibo.csv')

if __name__ == '__main__':
    start = time.time()
    #正则匹配主题，表情，@，url，无实际含义内容，非城市字符，停用字，
    #白名单与创造101高度相关的词，较相关词，可能相关的短词，黑名单与创造101基本毫无关联的主题词，广告词，选手用户，官方微博账号，明显黑名单水军用户
    #打榜词汇，打榜主题，水军高发城市
    pattern_topic = re.compile(r'(#[^#]+#)')
    pattern_facial = re.compile(r'(\[[^\]]+\])')
    #pattern_at = re.compile(r'(@[^\s|:|：|(|)|#|@|[http:]|\[]+)')
    pattern_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    pattern_nothing= re.compile(r'([\d|a-zA-Z|一|二|三|四|五|六|七|八|九|十|就]+)')
    pattern_nocity = re.compile(r'([".。/\da-zA-Z]+|[我们]|[用户] )')
    pattern_name = re.compile(r'([\u4e00-\u9fa5]+[_]+[a-zA-Z\d]+)')
    stopwords = ['分','享','微','博','下','评','论','顶','个','一','转','发','元','芳','来','了']

    whiteList_high = list(pd.read_csv('keyword/whiteList_high.csv')['关键词'])
    whiteList = list(pd.read_csv('keyword/whiteList.csv')['关键词'])
    shortword = list(pd.read_csv('keyword/shortword.csv')['关键词'])
    blackList = list(pd.read_csv('keyword/blackList.csv')['关键词'])
    adword = list(pd.read_csv('keyword/ad.csv')['广告词'])
    star = list(pd.read_csv('keyword/star.csv')['用户'])
    official = list(pd.read_csv('keyword/official.csv')['官方用户'])
    blackuser = list(pd.read_csv('keyword/blackuser.csv')['明显水军用户'])
    callList = list(pd.read_csv('keyword/call.csv')['关键字'])
    callList2 = list(pd.read_csv('keyword/call2.csv')['打榜'])
    blackcity = list(pd.read_csv('keyword/blackcity.csv')['水军高发城市'])

    #数据预处理第一步，去除格式不符的数据，标记内容，按日期分配文件
    begin = time.time()
    date = pre_first('data','pre_first')
    print('完成数据分配预处理，耗费%f小时'%((time.time()-begin)/3600))

    #数据预处理第二步，从转发内容中提取一些原创项目中可能没有的原创内容,分发到各个相应日期中
    begin = time.time()
    pre_second(date, 'data', 'pre_first')
    print('完成从转发内容中提取原创并分配，耗费%f小时'%((time.time()-begin)/3600))

    #预处理第三步，内容识别，将之前标记识别分类分开；行为识别，去除一个用户一天内多次发布相同内容
    begin = time.time()
    pre_third('pre_first','pre_second')
    print('完成内容和行为识别去重，耗费%f小时'%((time.time()-begin)/3600))

    #用户特征统计
    begin = time.time()
    user_repost,user_repost_num,user_original,user_active,weibo_all = pre_fourth('pre_second')
    print('完成统计用户数据，耗费%f小时'%((time.time()-begin)/3600))

    #向原创和转发中添加转发量等特征,做第二次内容筛选
    begin = time.time()
    pre_fifth('pre_second',weibo_all,user_repost,user_repost_num,user_original,user_active)
    print('完成添加微博等任务，耗费%f小时'%((time.time()-begin)/3600))    

    #重新统计用户
    begin = time.time()
    user_repost,user_repost_num,user_original,user_active,weibo_all = pre_fourth('pre_second')
    print('完成统计用户数据，耗费%f小时'%((time.time()-begin)/3600))

    #重新添加用户特征到微博数据
    begin = time.time()
    pre_fifth('pre_second',weibo_all,user_repost,user_repost_num,user_original,user_active,check=False)
    print('完成添加微博信息，耗费%f小时'%((time.time()-begin)/3600))

    #重新分配文件夹，统计数量
    pre_six('pre_first','pre_second','result')
    print('一共耗费%f小时'%((time.time()-start)/3600))