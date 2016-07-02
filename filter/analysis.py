#-*- coding: utf-8 -*-

# Analysis different kinds of log data
# cid : 20740042X
# uid : 502819
import os
import math
import json

class Analyzer(object):
    """docstring for Analyzer"""
    def __init__(self, cid):
        super(Analyzer, self).__init__()
        self.result_dir = '../result/'
        self.c_id = cid

        # 学习行为的最大权值，等效与max_weight秒的视频
        self.max_weight = 60 * 20

        # 尽可能保证视频、讨论区、作业三部分的行为权值综合相等
        # 但是也可以通过下面的两个参数进行调节
        # sum(problem) = sum(video) * sum_problem_weight
        # sum(forum) = sum(video) * sum_forum_weight
        self.sum_problem_weight = 1.0
        self.sum_forum_weight = 1.0

        # 对讨论区某些行为的权值进行进行单独调整
        # weight(vote) = weight(create) * vote_over_create
        # weight(view) = weight(create) * view_over_create
        self.vote_over_create = 0.4
        self.view_over_create = 0.2
        # weight(save) = weight_min(check, graded, showanswer) * save_over_problem
        self.save_over_problem = 0.3

        # 七天为一个时间间隔进行统计
        # used in uid_time_distribution
        self.time_interval = 7

        # 每个部分最突出的学生数量，饼图中用到的
        # the maximum number of top student in each section
        self.max_top_student = 4

        # sankey图用到的参数，如何选择活跃学生
        # which kind of filter we use when selecting active student
        # if type = 0, 视频时间不少于sankey_video_least，同时有一个以上的作业/讨论区
        # if type = 1, 所有行为权值不少于sankey_threshold 
        # if type = 2, 排序，取前sankey_top_student人
        # if type = 3, type=0 + type=1
        # if type = 4, type=1 + type=2
        # if type = 5, type=0 + type=2
        self.filter_type = 0
        self.sankey_video_least = 300       # parameter for type = 0
        self.sankey_threshold = 1000        # parameter for type = 1
        self.sankey_top_student = 100        # parameter for type = 2

        # 调试
        self.debug_counter1 = 0
        self.debug_counter2 = 0

        # 学习行为的权值
        self.event_param = {
            'watch_video': 0.0,
            'view_forum': 0.0,
            'django_comment_client.base.views.vote_for_thread': 0.0,
            'django_comment_client.base.views.vote_for_comment': 0.0, 
            'django_comment_client.base.views.update_comment': 0.0,
            'django_comment_client.base.views.create_comment': 0.0,
            'showanswer': 0.0,
            'problem_save': 0.0,
            'problem_check': 0.0,
            'problem_graded': 0.0
        }

        # 学习行为的类型
        self.forum_type = {
            'view_forum',
            'django_comment_client.base.views.vote_for_thread',
            'django_comment_client.base.views.vote_for_comment', 
            'django_comment_client.base.views.update_comment',
            'django_comment_client.base.views.create_comment'
        }
        self.problem_type = {
            'showanswer',
            'problem_save',
            'problem_check',
            'problem_graded'
        }
    
    def load_structure(self):
        self.ordered_structure = list()
        self.course_structure = dict()
        self.course_mapping = dict()

        filename = self.result_dir + self.c_id + '.course_structure'
        file_handle = open(filename, 'r', encoding='utf-8')
        try:
            self.course_structure = json.loads(file_handle.readline(), strict=False)
            self.course_mapping = json.loads(file_handle.readline(), strict=False)
            self.ordered_structure = json.loads(file_handle.readline(), strict=False)
        except(ValueError, KeyError):
            print ('error loading course structure')
        file_handle.close()

    def show_event_param(self):
        print ('--------All types of event--------')
        for i in self.event_param:
            print (i + '\t' + repr(self.event_param[i]))
        print ('--------End of event types--------')

    def calc_weight_from_count(self):
        # make sure the sum of problem and sum of forum equals to watch_video
        each_sum_weight = self.event_param['watch_video'] / len(self.problem_type) * self.sum_problem_weight
        for i in self.problem_type:
            self.event_param[i] = each_sum_weight / self.event_param[i]
        min_val = 1000000000000.0
        for i in self.problem_type:
            if i != 'problem_save' and self.event_param[i] < min_val:
                min_val = self.event_param[i]
        self.event_param['problem_save'] = min_val * self.save_over_problem

        # the sum of forum equals to watch_video
        '''
            weight(create) * (create_comment + update_comment) + 
            weight(vote) * (vote_for_thread + vote_for_comment) + 
            weight(view) * view_forum
             = self.sum_forum_weight * watch_video
        '''
        weighted_sum = 0.0
        weighted_sum += self.event_param['django_comment_client.base.views.create_comment']
        weighted_sum += self.event_param['django_comment_client.base.views.update_comment']
        weighted_sum += self.vote_over_create * self.event_param['django_comment_client.base.views.vote_for_thread']
        weighted_sum += self.vote_over_create * self.event_param['django_comment_client.base.views.vote_for_comment']
        weighted_sum += self.view_over_create * self.event_param['view_forum']

        weight_for_create = self.sum_forum_weight * self.event_param['watch_video'] / weighted_sum
        self.event_param['django_comment_client.base.views.create_comment'] = weight_for_create
        self.event_param['django_comment_client.base.views.update_comment'] = weight_for_create
        self.event_param['watch_video'] = 1.0

        # set max weight
        for i in self.event_param:
            if self.event_param[i] > self.max_weight:
                self.event_param[i] = self.max_weight

        # change forum weight
        self.event_param['django_comment_client.base.views.vote_for_thread'] = \
            self.vote_over_create * self.event_param['django_comment_client.base.views.create_comment']
        self.event_param['django_comment_client.base.views.vote_for_comment'] = \
            self.vote_over_create * self.event_param['django_comment_client.base.views.create_comment']
        self.event_param['view_forum'] = \
            self.view_over_create * self.event_param['django_comment_client.base.views.create_comment']

        print ('Show weight of different event')
        self.show_event_param()

    def load_param(self):
        filename = self.result_dir + self.c_id + '.data_count'
        try:
            self.event_param = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading data count file')
    
    def load_weight(self):
        '''
            the parameter file only consists of the count of each kind of log data
            you still need to re-calculate the weight, because the algorithm to calc weight is not fixed yet
        '''
        self.load_param()
        self.calc_weight_from_count()

    def log_data_count(self):
        '''
            count the number of different log event type
        '''
        filename = self.result_dir + self.c_id + '.date_course'
        print ('loading data file')
        try:
            date_course_dict = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading all course data')
        print ('loading succeed')

        for date in date_course_dict:
            for course in date_course_dict[date]:
                for log in date_course_dict[date][course]:
                    event_type = log['event_type']
                    if event_type == 'watch_video':
                        self.event_param[event_type] += log['time1']
                    # add deep analysis of problem data
                    # count the number of problems
                    elif event_type in self.problem_type:
                        cc = self.__parse_problem_log_count(log)
                        self.event_param[event_type] += cc
                    else:
                        self.event_param[event_type] += 1
        self.show_event_param()

        outfile = self.result_dir + self.c_id + '.data_count'
        output = open(outfile, 'w')
        output.write(json.dumps(self.event_param) + '\n')
        output.close()

    def __build_match_from_zero(self, old_dict):
        dict_to_num = dict()
        counter = 0
        for i in old_dict:
            dict_to_num[i] = counter
            counter += 1
        return dict_to_num

    def __build_match_from_zero_include(self, old_dict, include_dict):
        dict_to_num = dict()
        counter = 0
        for i in old_dict:
            if old_dict[i] not in include_dict:
                continue
            dict_to_num[i] = counter
            counter += 1
        return dict_to_num

    def __reverse_dict_to_sorted_array(self, old_dict):
        sorted_date = sorted(list(old_dict))
        sorted_arr = list()
        for i in sorted_date:
            data_id = old_dict[i]
            sorted_arr.append( [i, data_id] )
        return sorted_arr

    def uid_time_distribution(self, date_course_dict):
        '''
            calculate the time distribution of the number of users that are active
            time_interval: unique UID is calculated in #time_interval days
        '''
        date_num_of_user = dict()
        
        # calculate the number of UID in each day
        log_counter = 0
        for date in date_course_dict:
            date_num_of_user[date] = set()
            for thread in date_course_dict[date]:
                log_counter += len(date_course_dict[date][thread])
                for log in date_course_dict[date][thread]:
                    event_type = log['event_type']
                    uid = log['context']['user_id']
                    date_num_of_user[date].add(uid)
        print ('total %d log data ' % (log_counter))

        sorted_date = sorted(date_num_of_user.items(), key=lambda asd:asd[0], reverse=False)

        for i in range(self.time_interval):
            sorted_date.append( ('', set()) )

        # interval_count count the number of UID in [i, i + time_interval)
        interval_count = list()
        for i in range(len(date_num_of_user)):
            s = set()
            for j in range(self.time_interval):
                s = s | sorted_date[i+j][1]
            interval_count.append( len(s) )

        for i in range(len(date_num_of_user) - self.time_interval, len(date_num_of_user)):
            s = set()
            for j in range(self.time_interval):
                s = s | sorted_date[i-j][1]
            interval_count[i] = len(s)

        # log the value, then 
        min_val = min(interval_count)
        for i in range(len(interval_count)):
            interval_count[i] = 1 + math.log(interval_count[i] / min_val)
        #for i in interval_count:
        #    print (i)
        return interval_count

    def to_streamgraph_data(self, matrix, date_to_num, threads_to_num, time_interval_uid):
        sorted_date_id = self.__reverse_dict_to_sorted_array(date_to_num)
        sorted_thread_id = self.__reverse_dict_to_sorted_array(threads_to_num)

        for i in range(len(sorted_thread_id)):
            sorted_thread_id[i][0] = self.course_mapping[ sorted_thread_id[i][0] ]

        tmp_list = list()
        for i in self.ordered_structure:
            for j in sorted_thread_id:
                if j[0] == i:
                    tmp_list.append(j)
                    break
        sorted_thread_id = tmp_list
        
        outfile = self.result_dir + self.c_id + '.streamdata.csv'
        output = open(outfile, 'w', encoding='utf-8')
        output.write('key,value,date' + '\n')
        for thread in sorted_thread_id:
            thread_name = thread[0]
            thread_id = thread[1]
            i = 0
            for date in sorted_date_id:
                date_name = date[0]
                date_id = date[1]
                output.write('%s,%f,%s\n' % (thread_name, time_interval_uid[i] * matrix[date_id][thread_id], date_name[2:]))
                i += 1
        output.close()        

    def __parse_problem_log_count(self, log):
        event_type = log['event_type']
        event = log['event']
        if event_type == 'problem_save':
            value = event.count('&') + 1
            return value
        elif event_type == 'problem_check':
            value = len(event['submission'])
            value += event['grade']
            return value
        else:
            # problem_graded is similar to problem_check
            # so, return 1, do not calculate the details in it
            # showanswer has the weight of 1
            return 1

    def calc_stream_value(self):
        import numpy
        '''
            generated the data file needed by stream graph
        '''
        filename = self.result_dir + self.c_id + '.date_course'
        print ('loading data file')
        try:
            date_course_dict = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading all course data')
        print ('loading succeed')

        time_interval_uid = self.uid_time_distribution(date_course_dict)

        self.load_structure()
        num_of_threads = len(self.course_structure)
        num_of_date = len(date_course_dict)
        threads_to_num = self.__build_match_from_zero_include(self.course_mapping, self.course_structure)
        date_to_num = self.__build_match_from_zero(date_course_dict)
        print ('--------Total %d date and %d threads--------' % (num_of_date, num_of_threads))

        date_thread_value = numpy.zeros([num_of_date, num_of_threads])

        output = open('temp', 'w')

        # calculate weighted value
        for date in date_course_dict:
            for thread in date_course_dict[date]:
                x = date_to_num[date]
                y = threads_to_num[thread]
                for log in date_course_dict[date][thread]:
                    event_type = log['event_type']
                    value = 0
                    if event_type == 'watch_video':
                        value = log['time1']
                    # add deep analysis of problem data
                    # count the number of problems
                    elif event_type in self.problem_type:
                        value = self.__parse_problem_log_count(log)
                    else:
                        value = 1
                    date_thread_value[x][y] += value * self.event_param[event_type]

        self.to_streamgraph_data(date_thread_value, date_to_num, threads_to_num, time_interval_uid)

        output.close()

    def calc_pie_value_video(self, heriarchy):
        '''
            calculate the video value in this graph
        '''
        filename = self.result_dir + self.c_id + '.video_time'
        try:
            video_user_date = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('loading video data failed')

        filename = self.result_dir + self.c_id + '.structured_video'
        try:
            video_structure = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('loading video structure failed')

        # build reverse check table
        i4x_to_thread = dict()
        i4x_to_subthread = dict()
        for thread in video_structure:
            for subthread in video_structure[thread]:
                for i4x in video_structure[thread][subthread]:
                    i4x_to_thread[i4x] = thread
                    i4x_to_subthread[i4x] = subthread

        for i4x in video_user_date:
            thread = i4x_to_thread[i4x]
            subthread = i4x_to_subthread[i4x]
            if thread not in heriarchy:
                heriarchy[thread] = {'video' : dict(), 'problem' : dict(), 'forum' : dict()}
            if subthread not in heriarchy[thread]['video']:
                heriarchy[thread]['video'][subthread] = dict()
            for user in video_user_date[i4x]:
                # change from string uid to numeric uid
                user_i = int(user)
                if user_i not in heriarchy[thread]['video'][subthread]:
                    heriarchy[thread]['video'][subthread][user_i] = 0.0
                for date in video_user_date[i4x][user]:
                    heriarchy[thread]['video'][subthread][user_i] += video_user_date[i4x][user][date][0]

        print ('process video date finished')

    def calc_pie_value_problem_forum(self, heriarchy):
        filename = self.result_dir + self.c_id + '.date_course'
        print ('loading data file')
        try:
            date_course_dict = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading all course data')
        print ('loading succeed')

        print ('processing problem and forum')
        invalid_counter = 0

        for date in date_course_dict:
            for thread in date_course_dict[date]:
                if thread not in heriarchy:
                    heriarchy[thread] = {'video' : dict(), 'problem' : dict(), 'forum' : dict()}
                for log in date_course_dict[date][thread]:
                    event_type = log['event_type']
                    # watch video will be processed later
                    if event_type == 'watch_video':
                        continue
                    if log['context']['user_id'] == '':
                        invalid_counter += 1
                        continue

                    # calculate value, consider right and wrong for problem log
                    value = 0
                    if event_type in self.problem_type:
                        value = self.__parse_problem_log_count(log)
                    else:
                        value = 1

                    # change to top type
                    top_type = ''
                    if event_type in self.problem_type:
                        top_type = 'problem'
                    elif event_type in self.forum_type:
                        top_type = 'forum'
                    if top_type == '':
                        assert(False);

                    # consider user in this section
                    uid = int(log['context']['user_id'])
                    if uid not in heriarchy[thread][top_type]:
                        heriarchy[thread][top_type][uid] = 0.0
                    heriarchy[thread][top_type][uid] += value * self.event_param[event_type]

        print ('process problem forum succeed')
        print ('Total %d invalid counter' % (invalid_counter))

    def calc_pie_value_user_sorted(self, heriarchy):
        print ('sorting results')
        for thread in heriarchy:
            for top_type in heriarchy[thread]:
                if top_type in {'problem', 'forum'}:
                    heriarchy[thread][top_type] = sorted(heriarchy[thread][top_type].items(),
                                                key=lambda asd:asd[1], reverse=True)
                elif top_type == 'video':
                    for subthread in heriarchy[thread][top_type]:
                        heriarchy[thread][top_type][subthread] = sorted(heriarchy[thread][top_type][subthread].items(),
                                                                key=lambda asd:asd[1], reverse=True)
        
    def merge_dict(self, all_value, old_list):
        for i in old_list:
            if i[0] not in all_value:
                all_value[i[0]] = 0.0
            all_value[i[0]] += i[1]

    def calc_pie_value_top(self, heriarchy):
        print ('calculate top student in each level')
        # the leaf level
        print ('leaf level')

        for thread in heriarchy:
            for top_type in heriarchy[thread]:
                if top_type in {'problem', 'forum'}:
                    value_sum = 0.0
                    heriarchy[thread][top_type] = {'top': list(), 'value': 0.0, 'user': heriarchy[thread][top_type]}
                    for item in heriarchy[thread][top_type]['user']:
                        value_sum += item[1]
                    heriarchy[thread][top_type]['value'] = value_sum
                    for i in range( min(self.max_top_student, len(heriarchy[thread][top_type]['user'])) ):
                        heriarchy[thread][top_type]['top'].append( heriarchy[thread][top_type]['user'][i][0] )
                elif top_type == 'video':
                    for subthread in heriarchy[thread][top_type]:
                        heriarchy[thread][top_type][subthread] = {'top' : list(), 'value': 0.0, 'user': heriarchy[thread][top_type][subthread]}
                        value_sum = 0.0
                        for item in heriarchy[thread][top_type][subthread]['user']:
                            value_sum += item[1]
                        heriarchy[thread][top_type][subthread]['value'] = value_sum
                        for i in range( min(self.max_top_student, len(heriarchy[thread][top_type][subthread]['user'])) ):
                            heriarchy[thread][top_type][subthread]['top'].append( int(heriarchy[thread][top_type][subthread]['user'][i][0]) )
        # inner level, for video only
        print ('inner level for video')
        for thread in heriarchy:
            for top_type in heriarchy[thread]:
                if top_type == 'video':
                    all_value = dict()
                    for subthread in heriarchy[thread][top_type]:
                        self.merge_dict(all_value, heriarchy[thread][top_type][subthread]['user'])
                    sorted_ans = sorted(all_value.items(), key=lambda asd:asd[1], reverse=True)
                    heriarchy[thread][top_type]['user'] = sorted_ans
                    heriarchy[thread][top_type]['value'] = 0.0  # this does not matter, it will calculate from leaf node
                    heriarchy[thread][top_type]['top'] = list()
                    for i in range( min(self.max_top_student, len(sorted_ans)) ):
                        heriarchy[thread][top_type]['top'].append(sorted_ans[i][0])

        # thread level, thread level
        print ('thread level')
        for thread in heriarchy:
            all_value = dict()
            for top_type in heriarchy[thread]:
                self.merge_dict(all_value, heriarchy[thread][top_type]['user'])
            sorted_ans = sorted(all_value.items(), key=lambda asd:asd[1], reverse=True)
            heriarchy[thread]['top'] = list()
            for i in range(min(self.max_top_student, len(sorted_ans))):
                heriarchy[thread]['top'].append(sorted_ans[i][0])

    def load_all_names(self):
        '''
            load all the related names, they can be checked by user_id
        '''
        filename = self.result_dir + self.c_id + '.allnames'
        try:
            content = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading all names')

        uid_to_name = dict()
        for i in content:
            uid_to_name[ i[1] ] = i[3]
        return uid_to_name

    def to_pie_graph_data(self, heriarchy):
        uid_to_name = self.load_all_names()
        self.load_structure()
        type_mapping = {'video': '视频', 'problem': '作业', 'forum': '讨论区'}
        tree = dict()
        tree['name'] = repr(self.c_id)
        tree['top'] = list()
        tree['children'] = list()
        for thread in heriarchy:
            if thread in {'top', 'user', 'value'}:
                continue
            # change to chinese name
            for i in range(len(heriarchy[thread]['top'])):
                heriarchy[thread]['top'][i] = uid_to_name[ heriarchy[thread]['top'][i] ]
            thread_dict = {'name': self.course_mapping[thread], 'children': list(), 
                            'top': heriarchy[thread]['top'], 'value': 0.0}
            for top_type in heriarchy[thread]:
                if top_type in {'top', 'user', 'value'}:
                    continue

                # change to chinese name
                for i in range(len(heriarchy[thread][top_type]['top'])):
                    heriarchy[thread][top_type]['top'][i] = uid_to_name[ heriarchy[thread][top_type]['top'][i] ]
                top_type_dict = {'name': type_mapping[top_type], 'children': list(), 
                                'top': heriarchy[thread][top_type]['top'], 'value': heriarchy[thread][top_type]['value']}
                if top_type == 'video':
                    for subthread in heriarchy[thread][top_type]:
                        if subthread in {'top', 'user', 'value'}:
                            continue

                        # change to chinese name
                        for i in range(len(heriarchy[thread][top_type][subthread]['top'])):
                            heriarchy[thread][top_type][subthread]['top'][i] = uid_to_name[ heriarchy[thread][top_type][subthread]['top'][i] ]
                        subthread_dict = {'name': self.course_mapping[subthread], 'value': heriarchy[thread][top_type][subthread]['value'],
                                            'top': heriarchy[thread][top_type][subthread]['top'] }
                        top_type_dict['children'].append(subthread_dict)
                thread_dict['children'].append( top_type_dict )
            tree['children'].append( thread_dict )

        outfile = self.result_dir + self.c_id + '.pie_graph.json'
        output = open(outfile, 'w', encoding='utf-8')
        # dump the json file with order, to make sure the pie graph is in order
        output.write('''{\n"name": "%s", \n "top": [], \n "children": [ \n''' % (self.c_id))
        counter = 0
        for i in self.ordered_structure:
            for child in tree['children']:
                if child['name'] == i:
                    output.write(json.dumps(child, indent=4, ensure_ascii=False) + '\n')
                    if counter != len(self.ordered_structure) - 1:
                        output.write(",")
                    break
            counter += 1
        output.write(''']\n }\n''')
        output.close()

    def calc_pie_graph_value(self):
        '''
            generate the data file needed by the pie graph
        '''
        heriarchy = dict()
        self.calc_pie_value_problem_forum(heriarchy)
        self.calc_pie_value_video(heriarchy)
        self.calc_pie_value_user_sorted(heriarchy)
        self.calc_pie_value_top(heriarchy)
        self.to_pie_graph_data(heriarchy)

    def calc_week_score(self, week_score):
        # load all log data, reparse them by week and uid

        filename = self.result_dir + self.c_id + '.date_course'
        print ('loading data file')
        try:
            date_course_dict = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading all course data')
        print ('loading succeed')

        print ('processing problem and forum')

        # parse all date by week
        all_dates = [date for date in date_course_dict]
        all_dates.sort()
        all_weeks = dict()
        for i in range(0, len(all_dates)):
            all_weeks[all_dates[i]] = int(i / 7)

        invalid_counter = 0
        for date in date_course_dict:
            which_week = all_weeks[date]
            if which_week not in week_score:
                week_score[which_week] = dict()
            for thread in date_course_dict[date]:
                for log in date_course_dict[date][thread]:
                    event_type = log['event_type']
                    # watch video will be processed later
                    if event_type == 'watch_video':
                        invalid_counter += 1
                        continue
                    uid = log['context']['user_id']
                    if uid == '':
                        invalid_counter += 1
                        continue

                    if uid not in week_score[which_week]:
                        week_score[which_week][uid] = list()
                    week_score[which_week][uid].append(log)
        print ('finish forum and problem data, total %d invalid' % (invalid_counter))
        invalid_counter = 0

        filename = self.result_dir + self.c_id + '.video_time'
        try:
            video_user_date = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('loading video data failed')

        for vid in video_user_date:
            for uid in video_user_date[vid]:
                for date in video_user_date[vid][uid]:
                    # the convert from string uid to numeric uid
                    uid_num = int(uid)
                    which_week = all_weeks[date]
                    if which_week not in week_score:
                        week_score[which_week] = dict()
                    # the last record in week_score[which_week][uid] is the length of video
                    if uid_num not in week_score[which_week]:
                        week_score[which_week][uid_num] = list()
                        week_score[which_week][uid_num].append( {'watch_video': video_user_date[vid][uid][date][0] } )
                        continue
                    elif 'watch_video' not in week_score[which_week][uid_num][-1]:
                        week_score[which_week][uid_num].append( {'watch_video': video_user_date[vid][uid][date][0] } )
                    else:
                        week_score[which_week][uid_num][-1]['watch_video'] += video_user_date[vid][uid][date][0]
        print ('finish video data, total %d invalid' % (invalid_counter))

        # here, for each uid, we calculate the earlist and latest time of the log data
        earlist = dict()
        latest = dict()
        for date in date_course_dict:
            which_week = all_weeks[date]
            for thread in date_course_dict[date]:
                for log in date_course_dict[date][thread]:
                    # remove some of the invalid data
                    if log['event_type'] == 'watch_video' and log['time1'] == 0:
                        continue
                    user_id = log['context']['user_id']
                    if user_id not in earlist or which_week < earlist[user_id]:
                        earlist[user_id] = which_week
                    if user_id not in latest or which_week > latest[user_id]:
                        latest[user_id] = which_week
        return earlist, latest

    def apply_filter_absolute_count(self, log_list):
        # watch at least self.sankey_video_least seconds of video
        if 'watch_video' not in log_list[-1]:
            return False
        elif log_list[-1]['watch_video'] < self.sankey_video_least:
            return False
        # the last record of this user must be watch_video
        log_list.pop()

        #self.debug_counter1 += 1
        # if it has any related log about problem or forum, then this student is active
        if len(log_list) > 0:
            #self.debug_counter2 += 1
            return True
        return False

    def apply_filter_absolute_value(self, log_list):
        # calculate the score this week
        total_score = 0
        if 'watch_video' in log_list[-1]:
            total_score += log_list[-1]['watch_video']
            log_list.pop()
        for log in log_list:
            event_type = log['event_type']
            counter = 0
            if event_type in self.problem_type:
                counter = self.__parse_problem_log_count(log)
            else:
                counter = 1
            total_score += counter * self.event_param[event_type]
        return total_score

    def apply_filter_relative_value(self, log_list):
        # still need to calculate the value
        # then sort the value, and choose only the top ones
        return self.apply_filter_absolute_value(log_list)

    def apply_filter_active_user(self, week_score, active_user):
        for week in week_score:
            active_user[week] = set()
            temp_dict = dict()
            for uid in week_score[week]:
                if self.filter_type == 0:
                    rtv = self.apply_filter_absolute_count(week_score[week][uid])
                    if rtv == True:
                        active_user[week].add(uid)
                elif self.filter_type == 1:
                    rtv = self.apply_filter_absolute_value(week_score[week][uid])
                    if rtv > self.sankey_threshold:
                        active_user[week].add(uid)
                elif self.filter_type == 2:
                    rtv = self.apply_filter_relative_value(week_score[week][uid])
                    temp_dict[uid] = rtv
                elif self.filter_type == 3: # combined filter: absolute_count + absolute_value
                    rtv = self.apply_filter_absolute_count(week_score[week][uid])
                    if rtv == False:
                        continue
                    rtv = self.apply_filter_absolute_value(week_score[week][uid])
                    if rtv > self.sankey_threshold:
                        active_user[week].add(uid)
                elif self.filter_type == 4: # combined filter: absolute_value + relative_value
                    rtv = self.apply_filter_absolute_value(week_score[week][uid])
                    if rtv < self.sankey_threshold:
                        continue
                    temp_dict[uid] = rtv
                elif self.filter_type == 5: # combined filter: absolute_count + relative_value
                    rtv = self.apply_filter_absolute_count(week_score[week][uid])
                    if rtv == False:
                        continue
                    rtv = self.apply_filter_absolute_value(week_score[week][uid])
                    temp_dict[uid] = rtv
            # sort by value, and record only the top ones
            if self.filter_type == 2 or self.filter_type == 4 or self.filter_type == 5:
                sorted_user = sorted(temp_dict.items(), key=lambda asd:asd[1], reverse=True)
                num_of_student = min(self.sankey_top_student, len(sorted_user))
                for i in range(0, num_of_student):
                    active_user[week].add(sorted_user[i][0])

    def apply_filter(self, week_score):
        '''
            apply different kinds of filter to week_score
        '''
        active_user = dict()
        self.apply_filter_active_user(week_score, active_user)
        return active_user

    def to_sankey_graph_data(self, active_user, earlist, latest):
        # definition of the different name templates
        active_template = 'Week%d_Active'
        new_template = 'Week%d_New'
        # never_new means this user has no activity before
        never_new_template = 'Week%d_NNew'
        nactive_template = 'Week%d_NActive'
        # never_nactive means this user has no activity later
        never_nactive_template = 'Week%d_NNactive'
        # the active connection between two weeks
        active_link_template = 'Week%d_Active_Week%d_Active'

        # the whole data structure for sankey
        data = {"nodes": list(), "links": list(), "names": dict()}

        # change uid to name
        uid_to_name = self.load_all_names()
        for week in active_user:
            temp_list = list()
            for uid in active_user[week]:
                temp_list.append(uid_to_name[int(uid)])
            active_user[week] = set(temp_list)
        # change earlist and latest to name
        temp_dict = dict()
        for uid in earlist:
            temp_dict[ uid_to_name[int(uid)] ] = earlist[uid]
        earlist = temp_dict
        temp_dict = dict()
        for uid in latest:
            temp_dict[ uid_to_name[int(uid)] ] = latest[uid]
        latest = temp_dict

        # construct sankey data structure
        num_of_weeks = len(active_user)
        # construct nodes
        data['nodes'].append(['Week1_Active', 'Week2_New', 'Week2_NNew'])
        for i in range(num_of_weeks-2):
            active_name = active_template % (i + 2)
            new_name = new_template % (i + 3)
            never_new_name = never_new_template % (i + 3)
            nactive_name = nactive_template % (i + 2)
            never_nactive_name = never_nactive_template % (i + 2)
            # now at every inner week, there are total 5 nodes
            data['nodes'].append([never_nactive_name, nactive_name, active_name, new_name, never_new_name])
        active_name = active_template % (num_of_weeks)
        nactive_name = nactive_template % (num_of_weeks)
        never_nactive_name = never_nactive_template % (num_of_weeks)
        data['nodes'].append([never_nactive_name, nactive_name, active_name])

        # construct names
        for i in range(num_of_weeks):
            active_name = active_template % (i + 1)
            data['names'][active_name] = active_user[i]
        for i in range(1, num_of_weeks):
            # construct new and never_new
            new_name = new_template % (i + 1)
            never_new_name = never_new_template % (i + 1)
            data['names'][new_name] = set()
            data['names'][never_new_name] = set()
            temp_set = active_user[i] - active_user[i-1]
            for user in temp_set:
                if earlist[user] < i:
                    data['names'][new_name].add(user)
                elif earlist[user] == i:
                    data['names'][never_new_name].add(user)
                else:
                    # for debug
                    print ('!!!!!!!!!!Error, earlist dict error!!!!!!!!!!')
        for i in range(0, num_of_weeks-1):
            # construct nactive and never_nactive
            nactive_name = nactive_template % (i + 2)
            never_nactive_name = never_nactive_template % (i + 2)
            data['names'][nactive_name] = set()
            data['names'][never_nactive_name] = set()
            temp_set = active_user[i] - active_user[i + 1]
            for user in temp_set:
                if latest[user] > i:
                    data['names'][nactive_name].add(user)
                elif latest[user] == i:
                    data['names'][never_nactive_name].add(user)
                else:
                    # for debug
                    print ('!!!!!!!!!!Error, latest dict error!!!!!!!!!!')
        for i in range(0, num_of_weeks-1):
            link_name = active_link_template % (i+1, i+2)
            data['names'][link_name] = active_user[i] & active_user[i + 1]

        # construct links
        for i in range(1, num_of_weeks):
            # two active node, connecting two weeks
            w1a_name = active_template % (i)
            w2a_name = active_template % (i + 1)
            # two types of nactive node
            w2na_name = nactive_template % (i + 1)
            w2nna_name = never_nactive_template % (i + 1)
            # two types of new node
            w2n_name = new_template % (i + 1)
            w2nn_name = never_new_template % (i + 1)

            data['links'].append( [w1a_name, len(data['names'][w2nna_name]), w2nna_name] )
            data['links'].append( [w1a_name, len(data['names'][w2na_name]), w2na_name] )
            # connection between two active node
            data['links'].append( [w1a_name, len(data['names'][w1a_name] & data['names'][w2a_name]), w2a_name] )

            data['links'].append( [w2n_name, len(data['names'][w2n_name]), w2a_name] )
            data['links'].append( [w2nn_name, len(data['names'][w2nn_name]), w2a_name])

        for i in data['names']:
            data['names'][i] = list(data['names'][i])

        filename = self.result_dir + self.c_id + '.sankey.json'
        output = open(filename, 'w', encoding='utf-8')
        output.write(json.dumps(data, indent=4, ensure_ascii=False) + '\n')
        output.close()

    def calc_sankey_graph_value(self):
        '''
            generate the data file needed by the sankey graph
        '''
        week_score = dict()
        earlist, latest = self.calc_week_score(week_score)
        active_user = self.apply_filter(week_score)
        self.to_sankey_graph_data(active_user, earlist, latest)
        
    def test(self):
        # 统计所有log数据的数据量，为之后标定权值使用
        # 这个函数只用执行一遍就行，只要result文件夹里面有data_count文件，就可以不执行这一步了
        self.log_data_count()

        # 之后对于三种分析，都是load_weight + calc_XXX的形式
        self.load_weight()
        self.calc_stream_value()
        #self.calc_pie_graph_value()
        #self.calc_sankey_graph_value()

def main():
    a = Analyzer('20740042X')
    a.test()

if __name__ == '__main__':
    main()
