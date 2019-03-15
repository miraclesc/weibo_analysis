from pretreatment import *
#计算发布时间
def count_time(dict_result,input_file,minute=False):
    target_file = os.listdir(input_file)
    for file_temp in target_file:
        data = pd.read_csv(input_file + '/' + file_temp)
        if len(data) > 0:
            if minute==False:
                data['发布时间小时'] = data['发布时间'].str.split(' ',expand=True)[1].str.split(':',expand=True)[0]
                hours_temp = dict(data.groupby('发布时间小时').apply(count_group))
                dict_result = add_num(hours_temp,dict_result)
            else:
                data['发布时间分钟'] = data['发布时间'].str.split(' ',expand=True)[1]
                minute_temp = dict(data.groupby('发布时间分钟').apply(count_group))
                dict_result = add_num(minute_temp,dict_result)
    return dict_result

#获得一个日期的星期
def get_week_day(date):
    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    week_day_dict = {
        0 : '星期一',
        1 : '星期二',
        2 : '星期三',
        3 : '星期四',
        4 : '星期五',
        5 : '星期六',
        6 : '星期天',
    }
    day = date.weekday()
    return week_day_dict[day]

#计算星期下的平均微博量
def to_week():
    date = pd.read_csv('result/date_weibo.csv',index_col=0)
    date_day = list(date.index)
    weekday = []
    for day in date_day:
        weekday.append(get_week_day(str_toDatetime(day)))
    date['星期'] = weekday
    week_date = date.groupby('星期').mean()
    week_date.to_csv('week_date_mean.csv')

#计算多种单独特征,包括发布省份发布城市等
def count_analysis(input_file, variable, name):
    target_file = os.listdir(input_file)
    statistics = {}
    for file_temp in target_file:
        data = pd.read_csv(input_file + '/' + file_temp)
        if len(data) > 0:
            statistics = add_num(dict(data.groupby(variable).apply(count_group)),statistics)
    statistics_df = pd.DataFrame([statistics]).T
    statistics_df.columns = [name]
    return statistics_df

#统计原创内容词云
def count_content(input_file):
    target_file = os.listdir(input_file)
    content = []
    pure_content = []
    for file_temp in target_file:
        data = pd.read_csv(input_file + '/' + file_temp)
        content += list(data['微博内容'])
    for temp in content:
        pure_content.append(str(remove_format(temp,pattern_topic,pattern_facial,pattern_url)))
    txt = '。'.join(pure_content)
    jieba.analyse.set_stop_words('chineseStopWords.txt')
    Key = list(jieba.analyse.extract_tags(txt, topK=1000, withWeight=True))
    key_df = pd.DataFrame(Key)
    key_df.columns = ['词','词频']
    key_df.to_csv('word.csv')

#输出所有原创内容
def all_original(input_file):
    example = pd.read_csv('original/2018-4-1.csv')
    all_data = pd.DataFrame(columns=list(example.columns)+['发布日期'])
    target_file = os.listdir(input_file)
    for file_temp in target_file:
        date = file_temp.split('.')[0]
        data = pd.read_csv(input_file + '/' + file_temp)
        data['发布日期'] = date
        data = data[data['该条微博总体转发量'] != 0]
        all_data = all_data.append(data,ignore_index=True)
    return all_data

#随机颜色
def random_color_func(word=None, font_size=None, position=None,  orientation=None, font_path=None, random_state=None):
        h  = random.randint(0,355)
        s = int(100.0 * 255.0 / 255.0)
        l = int(100.0 * float(random.randint(60, 120)) / 255.0)
        return "hsl({}, {}%, {}%)".format(h, s, l)
#词云
def draw_colud(num_word):
    word = pd.read_csv('word.csv')
    word_top = list(word['词'])[:num_word]
    back_coloring = np.array(Image.open('image.jpg'))
    wordcloud = WordCloud(
        font_path='simfang.ttf',
        background_color="white",
        max_words=num_word, 
        mask=back_coloring,
        max_font_size=50,
        random_state=45,
    )
    wordcloud.generate(' '.join(word_top))
    image_colors = ImageColorGenerator(back_coloring)
    wordcloud.to_file('词云.jpg')

#提取每日词汇
def extract_key_day():
    word = pd.DataFrame()
    date_list = []
    target_file = os.listdir('original')
    for file_temp in target_file:
        date_list.append(file_temp.split('.')[0])
    for date in date_list:
        date_content = []
        hotword = []
        data_original = pd.read_csv('original/' + date + '.csv')
        date_content += list(data_original['微博内容'])
        try:
            data_repost = pd.read_csv('repost/' + date + '.csv')
            date_content += list(data_repost['全部内容'])
        except:
            pass   
        for content in date_content:
            content = str(remove_format(content,pattern_topic,pattern_facial,pattern_url))
            hotword.append(content)
        txt = '。'.join(hotword)
        jieba.analyse.set_stop_words('chineseStopWords.txt')
        Key = list(jieba.analyse.extract_tags(txt,topK=100,withWeight=False))
        word[date] = Key
    date_list = sorted(date_list, key=lambda date:get_timestamp(date,2))
    word = word[date_list]
    word.to_csv('word_day.csv')

#给每一个MID添加日期
def add_date_mid(dict_temp, dict_result, date):
    for key, item in dict_temp.items():
        if key not in dict_result:
            dict_result[key] = [{date: item}]
        else:
            dict_result[key].append({date: item})
    return dict_result
#计算一条有转发微博的有转发日期
def count_weaken(input_file):
    mid_date_count = {}
    target_file = os.listdir(input_file)
    for file_temp in target_file:
        date = file_temp.split('.')[0]
        data = pd.read_csv(input_file + '/' + file_temp)
        mid_count = dict(data.groupby('原创微博id').apply(count_group))
        mid_date_count = add_date_mid(mid_count,mid_date_count,date)
    return mid_date_count
#计算一条微博衰减天数
def attenuation_first(mid_date_count,all_original_data):
    all_original_data = all_original_data.sort_values(by='该条微博总体转发量',ascending=False)
    all_mid = list(all_original_data['MID'])
    all_date = list(all_original_data['发布日期'])
    weaken = {}
    for i in range(len(all_mid)):
        try:
            date_num_list = mid_date_count[all_mid[i]]
            for date_num in date_num_list:
                for key,item in date_num.items():
                    date_diff = (datetime.datetime.strptime(key,'%Y-%m-%d') - datetime.datetime.strptime(all_date[i],'%Y-%m-%d')).days
                    if all_mid[i] not in weaken:
                        weaken[all_mid[i]] = [{date_diff : item}]
                    else:
                        weaken[all_mid[i]].append({date_diff : item})
        except:
            pass
    return weaken
def attenuation_second(weaken):    
    new_mid = {}
    for key,item in weaken.items():
        day_list = [0] * 93
        sum_num = 0
        for i in range(len(item)):
            for day_diff, day_num in item[i].items():
                day_list[day_diff] = day_num
                sum_num += day_num
        day_list[91] = sum_num
        day_list[92] = len(item)
        new_mid[key] = day_list
        new_mid_df = pd.DataFrame(new_mid).T
    new_mid_df.rename(columns={91:'总量', 92:'周期'}, inplace = True)
    new_mid_df = new_mid_df.sort_values(by='总量',ascending=False)
    new_mid_df.to_csv('衰减天数.csv')
    return new_mid_df
def attenuation_third(new_mid_df):
    new_mid_all = np.array(new_mid_df['总量'])
    new_mid_all = new_mid_all.reshape((-1,1))
    new_mid_id = list(new_mid_df.index)
    del new_mid_df['总量']
    del new_mid_df['周期']
    new_mid_array = np.array(new_mid_df)
    percentage_array = new_mid_array / new_mid_all
    m,n = np.shape(percentage_array)
    cycle_day = []
    for i in range(m):
        cycle_day_temp = 0
        for j in range(n):
            if percentage_array[i,j] < 0.0001 and new_mid_array[i,j] <= 2:
                percentage_array[i,j] = 0
            else:
                cycle_day_temp += 1
        cycle_day.append(cycle_day_temp)
        
    cycle= pd.DataFrame([Counter(cycle_day)]).T
    cycle.to_csv('生命周期.csv')
    new_per_df = pd.DataFrame(percentage_array,index=new_mid_id)
    new_per_df['总量'] = new_mid_all
    new_per_df['周期'] = cycle_day
    #new_per_df = new_per_df.mean(axis=0)
    new_per_df.to_csv('衰减比例.csv')
    return new_per_df
#将计算衰减结果合并
def part_repost(all_original_data,new_per_df):
    all_original_data = all_original_data[all_original_data['该条微博总体转发量']>1]
    post_date = list(all_original_data['发布日期']) 
    MID = list(all_original_data['MID'])
    new_df = new_per_df[['周期']]
    cycle_list = []
    cycle_per = []
    for i in range(len(MID)):
        cycle_day = new_df.loc[MID[i],'周期']
        cycle_list.append(cycle_day)
        #向后占比
        day = (datetime.datetime.strptime('2018-7-1','%Y-%m-%d') - datetime.datetime.strptime(post_date[i],'%Y-%m-%d')).days
        cycle_per.append(cycle_day/day)
    all_original_data['有转发天数'] = cycle_list
    all_original_data['有转发天数向后占比'] = cycle_per
    all_original_data = all_original_data.sort_values(by=['有转发天数','有转发天数向后占比'],ascending=False)
    all_original_data.to_csv('部分有转发微博.csv',index=None)
    return all_original_data,new_df

#找到一条原创的所有转发微博
def find_all_repost(mid,all_original_data,mid_date_count,new_df):
    begin = time.time()
    repost = pd.DataFrame()
    date_list = mid_date_count[mid]
    for i in range(len(date_list)):
        for key in date_list[i].keys():
            temp = pd.read_csv('repost/' + key + '.csv')
            temp = temp[temp['原创微博id'] == mid]
            repost = repost.append(temp,ignore_index=True)
    user_original = all_original_data[all_original_data['MID'] == mid]
    try:
        level_rate = str(len(repost[repost['转发层级'] == '1级转发'])/len(repost))
    except:
        level_rate = 0
    return level_rate
    name = list(user_original['用户昵称'])[0]
    cycle = new_df.loc[mid,'周期']
    date_post = list(all_original_data[all_original_data['MID'] == mid]['发布日期'])[0]
    csv_name =  name + '_' + str(len(repost)) + '_' + str(level_rate) + '_' + str(cycle) + '_' + str(date_post)
    #命名规则：原创用户姓名 + 被转发量 + 1级转发占比 + 生命周期 + 发布时间
    repost.to_csv('forward/'+ csv_name + '.csv',index=None)
    print('完成%s，耗费%.2f分'%(csv_name,(time.time()-begin)/60))


#找到一位用户的所有原创或转发微博
def find_user_post(user_name,user,find_type,num):
    date_list = user.loc[user_name,'活跃日期'].split(',')
    result_data = pd.DataFrame()
    if find_type == '原创':
        if user.loc[user_name,'原创量'] == 0:
            return 0
        initial_file = 'original/'
        num_post = user.loc[user_name,'原创总体被转发']
    elif find_type == '转发':
        if user.loc[user_name,'转发量'] == 0:
            return 0
        initial_file = 'repost/'
        num_post = user.loc[user_name,'总体被转发'] -  user.loc[user_name,'原创总体被转发']
    index = 0
    for date in date_list:
        date = '-'.join(date.split('/'))
        try:
            data = pd.read_csv(initial_file + date + '.csv')
            data = data[data['用户昵称'] == user_name]
            if len(data) > 0:
                result_data = result_data.append(data,ignore_index=True)
        except:
            pass
        if len(result_data) > 100 or len(result_data) > num * 0.5:
            break
    #result_data = sort_date(result_data)
    #命名规则 用户昵称 类型 微博量 原创转发量/转发转发量
    result_data.to_csv('post/' + user_name+ '_' + find_type + '_' + str(len(result_data)) + '_' + str(num_post) +'.csv',index=None)
    return result_data

#根据不同的用户分类返回不同的关键词
def type_sort(input_file):
    target_file = os.listdir('post/'+input_file)
    content = []
    for file_temp in target_file:
        data = pd.read_csv('post/'+input_file+'/'+file_temp)
        content += list(data['微博内容'])
    content_df = pd.DataFrame(content)
    content_df.to_csv(input_file+'.csv',index=None)
    return 1
    hotword = []
    for temp in content:
        temp = str(remove_format(temp,pattern_topic,pattern_facial,pattern_url))
        hotword.append(temp)
    txt = '。'.join(hotword)
    jieba.analyse.set_stop_words('chineseStopWords.txt')
    Key = list(jieba.analyse.extract_tags(txt,topK=200,withWeight=False))
    return Key

#计算衰减部分
def col_attenuation():
    mid_date_count = count_weaken('repost')
    all_original_data = all_original('original')

    weaken =  attenuation_first(mid_date_count,all_original_data)
    new_mid_df = attenuation_second(weaken)
    #new_mid_df = pd.read_csv('衰减天数.csv',index_col=0)
    new_per_df = attenuation_third(new_mid_df)
    all_original_data,new_df = part_repost(all_original_data,new_per_df)
    return mid_date_count,all_original_data,new_df,weaken

#根据不同的用户分类返回不同的关键词
def type_sort(input_file):
    target_file = os.listdir('post/'+input_file)
    content = []
    for file_temp in target_file:
        data = pd.read_csv('post/'+input_file+'/'+file_temp)
        content += list(data['微博内容'])
    content_df = pd.DataFrame(content)
    content_df.to_csv(input_file+'.csv',index=None)
    return 1
    hotword = []
    for temp in content:
        temp = str(remove_format(temp,pattern_topic,pattern_facial,pattern_url))
        hotword.append(temp)
    txt = '。'.join(hotword)
    jieba.analyse.set_stop_words('chineseStopWords.txt')
    Key = list(jieba.analyse.extract_tags(txt,topK=200,withWeight=False))
    return Key

#将输入的文件导出gephi可识别的节点和边文件
def to_gephi(input_file,name):
    data  = pd.read_csv(input_file)
    data_level = data[['用户昵称','转发层级']].drop_duplicates(keep='first', inplace=False)
    data_level.index = data_level['用户昵称']
    network_name = data[['用户昵称','上级用户']]
    network_name.columns = ['target','source']
    network_name = network_name.drop_duplicates(keep='first', inplace=False)
    network_name.to_csv('edge_'+name+'.csv',index=None)
    #非叶节点用户
    network_name_num = network_name.groupby('source').count()
    all_user = [data.loc[0,'原创用户']] + list(data_level['用户昵称'])
    #节点权重计算
    weight = []
    level = []
    for user_name in all_user:
        try:
            weight.append(1+network_name_num.loc[user_name,'target'])
        except:
            weight.append(1)
        try:
            if type(data_level.loc[user_name,'转发层级']) == str:
                if int(data_level.loc[user_name,'转发层级'][0]) >= 5:
                    level.append('5')
                else:
                    level.append(data_level.loc[user_name,'转发层级'][0])
            else:
                level.append('6')
        except:
            level.append('0')
    node = pd.DataFrame([all_user,weight,level]).T
    node.columns = ['Id','weight','level']
    node= node.drop_duplicates(keep='first', inplace=False)
    node_weight = list(node['weight'])
    node_id = list(node['Id'])
    node_name = []
    for i in range(len(node_weight)):
        if node_weight[i]>= (len(data)*0.01):
            node_name.append(node_id[i])
        else:
            node_name.append('')
    node['name_part'] = node_name
    node.to_csv('node_'+name+'.csv',index=None)

#得到重点微博的一级转发率
def important_weibo(all_original_data):
    all_original_data = all_original_data[all_original_data['有转发天数']>=3]
    all_original_data = all_original_data[all_original_data['该条微博总体转发量']>=200]
    all_mid = list(all_original_data['MID'])
    all_level_rate = []
    index = 0
    for mid_this in all_mid:
        begin = time.time()
        all_level_rate.append(find_all_repost(mid_this,all_original_data,mid_date_count,new_df))
        print('完成%s耗费%.2f秒'%(mid_this,time.time()-begin))
    all_original_data['一级转发率'] = all_level_rate
    all_original_data = all_original_data.sort_values(by='一级转发率')
    all_original_data.to_csv('重点微博一级转发率排序.csv')

#找到一位用户的所有原创或转发微博
def find_user_post(user_name,user,find_type,*num):
    date_list = user.loc[user_name,'活跃日期'].split(',')
    result_data = pd.DataFrame()
    if find_type == '原创':
        if user.loc[user_name,'原创量'] == 0:
            return 0
        initial_file = 'original/'
        num_post = user.loc[user_name,'原创总体被转发']
    elif find_type == '转发':
        if user.loc[user_name,'转发量'] == 0:
            return 0
        initial_file = 'repost/'
        num_post = user.loc[user_name,'总体被转发'] -  user.loc[user_name,'原创总体被转发']
    index = 0
    for date in date_list:
        date = '-'.join(date.split('/'))
        try:
            data = pd.read_csv(initial_file + date + '.csv')
            data = data[data['用户昵称'] == user_name]
            if len(data) > 0:
                result_data = result_data.append(data,ignore_index=True)
        except:
            pass
        if num:
            if len(result_data) > 100 or len(result_data) > num * 0.5:
                break
    #result_data = sort_date(result_data)
    #命名规则 用户昵称 类型 微博量 原创转发量/转发转发量
    result_data.to_csv('post/' + user_name+ '_' + find_type + '_' + str(len(result_data)) + '_' + str(num_post) +'.csv',index=None)
    return result_data

#将喜欢一个明星的用户归为一类
def fans_group(star_list,end_num,user_top):
    star = list(pd.read_csv('star.csv')['用户'])
    official = list(pd.read_csv('official.csv')['官方用户'])
    for star_temp in star_list:
        jieba.add_word(star_temp, freq=None, tag='nr')
    index = 0
    user_list = list(user_top.index)
    user_ori = list(user_top['原创量'])
    user_rep = list(user_top['转发量'])
    fans_user = []
    fans_sort = []
    for i in range(len(user_list)):
        begin = time.time()
        if user_list[i] in official or user_list[i] in star:
            continue
        if user_ori[i] > user_rep[i]:
            user_data_use = find_user_post(user_list[i], user_top, '原创', user_ori[i])
            content_temp = list(user_data_use['微博内容'])
        else:
            user_data_use = find_user_post(user_list[i], user_top, '转发', user_rep[i])
            content_temp = list(user_data_use['全部内容'])
        try:
            sentence = '。'.join(content_temp)
        except:
            content_new = []
            for j in content_temp:
                content_new.append(str(j))
            sentence = '。'.join(content_new)
        key = jieba.analyse.extract_tags(sentence, topK=2, withWeight=True, allowPOS=('nr',))
        if key[0][1] >= 2:
            fans_user.append(user_list[i])
            fans_sort.append(key[0][0])
            index += 1
            print('完第%d位粉丝鉴定耗时%f'%(index,time.time()-begin))
        if index % 500 == 0:
            fans = pd.DataFrame([fans_user,fans_sort])
            fans = fans.T
            fans.columns = ['用户昵称','明星']
            fans.to_csv('relation.csv',index=None)
        if index == end_num:
            break
    fans = pd.DataFrame([fans_user,fans_sort])
    fans = fans.T
    fans.columns = ['用户昵称','明星']
    fans.to_csv('relation.csv',index=None)


def count_fans(df):
    fans_name = list(df['用户昵称'].drop_duplicates(keep='first'))
    return fans_name
def add_num_target(dict_temp, dict_result, target_user):
    for key, item in dict_temp.items():
        if key not in target_user:
            continue
        else:
            for item_user in item:
                if item_user not in target_user:
                    continue
                else:
                    if key not in dict_result:
                        dict_result[key] = []
                    if item_user not in dict_result[key]:
                        dict_result[key].append(item_user)
    return dict_result
#通过统计粉丝和明星的关系，找到共同喜好的用户
def fans_relation(star_name):
    relation = pd.read_csv('用户明星关系.csv',index_col=0)
    data_star = relation[relation['明星'] == star_name]
    data_fans = list(data_star.index)
    user_fans = {}
    input_file = 'repost'
    target_file = os.listdir(input_file)
    for file_temp in target_file:
        data = pd.read_csv(input_file + '/' + file_temp)
        user_fans_temp = dict(data.groupby('上级用户').apply(count_fans))
        user_fans = add_num_target(user_fans_temp,user_fans,data_fans)
    target_user = []
    source_user = []
    for key,item in user_fans.items():
        for item_temp in item:
            target_user.append(item_temp)
            source_user.append(key)
    relation_fans = pd.DataFrame([target_user,source_user]).T
    relation_fans.columns =  ['target','source']
    relation_fans.to_csv('relation_'+ star_name +'.csv',index=None)


pattern_topic = re.compile(r'(#[^#]+#)')
pattern_facial = re.compile(r'(\[[^\]]+\])')
pattern_at = re.compile(r'(@[^\s|,|。|，|:|)| |#|@|\[]+)')
pattern_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

user = pd.read_csv('user.csv',index_col=0)
user_top = user[:]
user_top['发博量'] = user_top['原创量'] + user_top['转发量']
user_top = user_top[user_top['发博量']>=100]
user_top = user_top.sort_values(by='发博量',ascending=False)
user_list = list(user_top.index)

mid_date_count,all_original_data,new_df,weaken = col_attenuation()

for user_this in user_list:
    begin = time.time()
    state = find_user_post(user_this, user, '原创')
    state = find_user_post(user_this, user, '转发')
    print('完成%s，耗费%.2f分'%(user_this,(time.time()-begin)/60))

fans_group(['黄子韬'], 3000, user_top)
fans_relation('孟美岐')

relationship = pd.read_csv('relation.csv',index_col=0)
acount_star = pd.DataFrame([Counter(relationship['明星'])]).T
acount_star.columns = ['忠实粉丝数']
acount_star = acount_star.sort_values(by='忠实粉丝数',ascending=False)
acount_star.to_csv('acount_star.csv')