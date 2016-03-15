#-*- coding: utf-8 -*-

# Analysis different kinds of log data
# cid : 20740042X
# uid : 502819
import os
import numpy
import json

class Analyzer(object):
    """docstring for Analyzer"""
    def __init__(self, cid):
        super(Analyzer, self).__init__()
        self.result_dir = '../result/'
        self.c_id = cid
        # the max weight for each event
        # one event equals to at most max_weight minutes of video watch
        self.max_weight = 10
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
        for i in self.event_param:
            if i != 'watch_video':
                self.event_param[i] = self.event_param['watch_video'] / self.event_param[i]
                if self.event_param[i] > self.max_weight:
                    self.event_param[i] = self.max_weight
        self.event_param['watch_video'] = 1.0
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

    def calc_weight(self):
        '''
            count the number of different log event type
        '''
        if os.path.exists(self.result_dir + self.c_id + '.data_count'):
            self.load_weight()
            return

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
                    elif event_type == 'problem_save' or event_type == 'problem_graded':
                        event = log['event']
                        cc = event.count('&')
                        if cc == 0:
                            cc = 1
                        self.event_param[event_type] += cc
                    elif event_type == 'problem_check':
                        event = log['event']
                        cc = len(event['submission'])   # the number of problems
                        cc += event['grade']            # how many are correct
                        self.event_param[event_type] += cc
                    else:
                        self.event_param[event_type] += 1
        self.event_param['watch_video'] /= 60   # count in minute
        self.show_event_param()

        outfile = self.result_dir + self.c_id + '.data_count'
        output = open(outfile, 'w')
        output.write(json.dumps(self.event_param) + '\n')
        output.close()

        self.calc_weight_from_count()

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

    def to_streamgraph_data(self, matrix, date_to_num, threads_to_num):
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
            for date in sorted_date_id:
                date_name = date[0]
                date_id = date[1]
                output.write('%s,%f,%s\n' % (thread_name, matrix[date_id][thread_id], date_name))
        output.close()

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

        self.load_structure()
        num_of_threads = len(self.course_structure)
        num_of_date = len(date_course_dict)
        threads_to_num = self.__build_match_from_zero_include(self.course_mapping, self.course_structure)
        date_to_num = self.__build_match_from_zero(date_course_dict)
        print ('--------Total %d date and %d threads--------' % (num_of_date, num_of_threads))

        date_thread_value = numpy.zeros([num_of_date, num_of_threads])

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
                    elif event_type == 'problem_save' or event_type == 'problem_graded':
                        event = log['event']
                        value = event.count('&')
                        if value == 0:
                            value = 1
                    elif event_type == 'problem_check':
                        event = log['event']
                        value = len(event['submission'])   # the number of problems
                        value += event['grade']            # how many are correct
                    else:
                        value = 1
                    date_thread_value[x][y] += value * self.event_param[event_type]

        self.to_streamgraph_data(date_thread_value, date_to_num, threads_to_num)

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
            heriarchy[thread]['video'][subthread][i4x] = dict()
            for user in video_user_date[i4x]:
                if user not in heriarchy[thread]['video'][subthread][i4x]:
                    heriarchy[thread]['video'][subthread][i4x][user] = 0.0
                for date in video_user_date[i4x][user]:
                    heriarchy[thread]['video'][subthread][i4x][user] += video_user_date[i4x][user][date][0]
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

                    # calculate value, consider right and wrong of problem
                    value = 0
                    if event_type == 'problem_save' or event_type == 'problem_graded':
                        event = log['event']
                        value = event.count('&')
                        if value == 0:
                            value == 1
                    elif event_type == 'problem_check':
                        event = log['event']
                        value = len(event(submission))
                        value += event['grade']
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

    def calc_user_sorted(self, heriarchy):
        print ('sorting results')
        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type in {'problem', 'forum'}:
                heriarchy[thread][top_type] = sorted(heriarchy[thread])
        for thread in heriarchy:
            for top_type in heriarchy[thread] and top_type == 'video':
                heriarchy[thread][top_type]

    def calc_pie_graph_value(self):
        '''
            generate the data file needed by the pie graph
        '''
        heriarchy = dict()
        self.calc_pie_value_problem_forum(heriarchy)
        self.calc_pie_value_video(heriarchy)
        self.calc_user_sorted(heriarchy)

    def test(self):
        #self.log_data_count()
        self.load_weight()
        self.calc_stream_value()

def main():
    a = Analyzer('20740042X')
    a.test()

if __name__ == '__main__':
    main()
    