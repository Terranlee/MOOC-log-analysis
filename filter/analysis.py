#-*- coding: utf-8 -*-

# Analysis different kinds of log data
# cid : 20740042X
# uid : 502819
import os
import math
import numpy
import json

class Analyzer(object):
    """docstring for Analyzer"""
    def __init__(self, cid):
        super(Analyzer, self).__init__()
        self.result_dir = '../result/'
        self.c_id = cid

        # the max weight for each event
        # one event equals to at most max_weight seconds of video watch
        self.max_weight = 60 * 20

        # sum(problem) = sum(video) * sum_problem_weight
        # sum(forum) = sum(video) * sum_forum_weight
        self.sum_problem_weight = 1.0
        self.sum_forum_weight = 1.0
        # weight(vote) = weight(create) * vote_over_create
        # weight(view) = weight(create) * view_over_create
        self.vote_over_create = 0.4
        self.view_over_create = 0.2
        # weight(save) = weight_min(check, graded, showanswer) * save_over_problem
        self.save_over_problem = 0.3

        # used in uid_time_distribution
        self.time_interval = 7

        # the maximum number of top student in each section
        self.max_top_student = 4
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
        self.course_structure = dict()
        self.course_mapping = dict()

        filename = self.result_dir + self.c_id + '.course_structure'
        file_handle = open(filename, 'r', encoding='utf-8')
        try:
            self.course_structure = json.loads(file_handle.readline(), strict=False)
            self.course_mapping = json.loads(file_handle.readline(), strict=False)
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
            heriarchy[thread]['video'][subthread] = dict()
            for user in video_user_date[i4x]:
                if user not in heriarchy[thread]['video'][subthread]:
                    heriarchy[thread]['video'][subthread][user] = 0.0
                for date in video_user_date[i4x][user]:
                    heriarchy[thread]['video'][subthread][user] += video_user_date[i4x][user][date][0]
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
        problem_value_types = {'problem_save', 'problem_graded', 'problem_check'}

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

                    # calculate value, consider right and wrong of problem
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
                    uid = log['context']['user_id']
                    if uid not in heriarchy[thread][top_type]:
                        heriarchy[thread][top_type][uid] = 0.0
                    heriarchy[thread][top_type][uid] += value * self.event_param[event_type]

        print ('process problem forum succeed')
        print ('Total %d invalid counter' % (invalid_counter))

    def calc_pie_value_user_sorted(self, heriarchy):
        print ('sorting results')
        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type in {'problem', 'forum'}:
                heriarchy[thread][top_type] = sorted(heriarchy[thread][top_type].items(),
                                                key=lambda asd:asd[1], reverse=True)
        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type == 'video':
                for subthread in heriarchy[thread][top_type]:
                    heriarchy[thread][top_type][subthread] = sorted(heriarchy[thread][top_type][subthread].items(),
                                                                key=lambda asd:asd[1], reverse=True)
    
    def merge_dict(self, all_value, old_list):
        for i in old_list:
            if i[0] not in all_value:
                all_value[i[0]] = 0.0
            all_value[i[0]] += i[1]

    def calc_pie_value_top(self, heriarchy):
        # the leaf level
        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type in {'problem', 'forum'}:
                value_sum = 0.0
                heriarchy[thread][top_type] = {'top': list(), 'value': 0.0, 'user': heriarchy[thread][top_type]}
                for item in heriarchy[thread][top_type]['user']:
                    value_sum += item[1]
                heriarchy[thread][top_type]['value'] = value_sum
                for i in range(self.max_top_student):
                    heriarchy[thread][top_type]['top'].append(heriarchy[thread][top_type]['user'][i][0])

        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type == 'video':
                for subthread in heriarchy[thread][top_type]:
                    heriarchy[thread][top_type][subthread] = {'top' : list(), 'value': 0.0, 'user': heriarchy[thread][top_type][subthread]}
                    value_sum = 0.0
                    for item in heriarchy[thread][top_type][subthread]['user']:
                        value_sum += item[1]
                    heriarchy[thread][top_type][subthread]['value'] = value_sum
                    for i in range(self.max_top_student):
                        heriarchy[thread][top_type][subthread]['top'].append(heriarchy[thread][top_type][subthread]['user'][i][0])

        # inner level
        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type == 'video':
                heriarchy[thread][top_type]['top'] = list()
                all_value = dict()
                for subthread in heriarchy[thread][top_type]:
                    self.merge_dict(all_value, heriarchy[thread][top_type][subthread]['user'])
                sorted_ans = sorted(all_value.items(), key=lambda asd:asd[1], reverse=True)
                for i in range(self.max_top_student):
                    heriarchy[thread][top_type]['top'].append(sorted_ans[i][0])
                heriarchy[thread][top_type]['user'] = sorted_ans
                heriarchy[thread][top_type]['value'] = 0.0  # this does not matter, it will calculate from leaf node

        # thread level
        for thread in heriarchy:
            heriarchy[thread]['top'] = list()
            all_value = dict()
            for top_type in heriarchy[thread]:
                self.merge_dict(all_value, heriarchy[thread][top_type]['user'])
            sorted_ans = sorted(all_value.items(), key=lambda asd:asd[1], reverse=True)
            for i in range(self.max_top_student):
                heriarchy[thread]['top'].append(sorted_ans[i][0])

    def to_pie_graph_data(self, heriarchy):
        tree = dict()
        tree['name'] = repr(self.c_id)
        tree['children'] = list()
        for thread in heriarchy:
            thread_dict = {'name': thread, 'children': list(), 
                            'top': heriarchy[thread]['top'], 'value': 0.0}
            for top_type in heriarchy[thread]:
                top_type_dict = {'name': top_type, 'children': list(), 
                                'top': heriarchy[thread][top_type]['top'], 'value': heriarchy[thread][top_type]['value']}
                if top_type == 'video':
                    for subthread in heriarchy[thread][top_type]:
                        subthread_dict = {'name': subthread, 'value': heriarchy[thread][top_type][subthread]['value'],
                                            'top': heriarchy[thread][top_type][subthread]['top'] }
                        top_type_dict['children'].append(subthread_dict)
                thread_dict['children'].append(top_type_dict)
            tree['children'].append( thread_dict )

        outfile = self.result_dir + self.c_id + '.pie_graph'
        output = open(outfile, 'w', encoding='utf-8')
        output.write(json.dumps(tree) + '\n')
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

    def test(self):
        #self.log_data_count()
        self.load_weight()
        self.calc_stream_value()
        #self.uid_time_distribution(date_course_dict)

def main():
    a = Analyzer('20740042X')
    a.test()

if __name__ == '__main__':
    main()
    