#-*- coding: utf-8 -*-

# Filter for xuetangX log data
# cid : 20740042X
# uid : 502819
import os
import re
import json
import gzip
import urllib.request
from bs4 import BeautifulSoup

class Filter(object):
    '''docstring for Filter
        This is a filter for log data from xuetangX.
        Use this to get all the data from a specific course, and do some basic statistics.
    '''

    def __init__(self, s_date, e_date, cid):
        super(Filter, self).__init__()
        # start_date and end_date are numbers like 20150715
        # course_id is the filter of different classes
        self.start_date = s_date
        self.end_date = e_date
        self.c_id = cid

        self.all_dirs = ['edxdbweb1', 'edxdbweb2', 'edxdbweb5', 'edxdbweb6']
        self.filelist = list()

    def __gen_gzfilelist_sub(self, rdir):
        for i in os.listdir(rdir):
            if i.endswith('.gz') and i.startswith('tracking.log-'):
                date = i[13:21]
                if date >= repr(self.start_date) and date <= repr(self.end_date):
                    self.filelist.append(rdir + i)

    def gen_gzfilelist(self):
        for i in self.all_dirs:
            self.__gen_gzfilelist_sub('/mnt/logs/' + i + '/log/tracking/')
        print ('Total %d files' % (len(self.filelist)))

    def __parse_gzfile_cid_sub(self, filename):
        ''' get the log data with a certain CID '''
        print ('parse ' + filename)
        counter = 0
        invalid_counter = 0
        valid_counter = 0
        cid_counter = 0
        for i in gzip.open(filename, 'rt'):
            counter += 1
            if counter % 100000 == 0:
                print (counter)
            try:
                content = json.loads(i, strict=False)
                cid = content['context']['course_id']
                # in this step we just filter all the log data related to course_id
                if cid.find(self.c_id) != -1:
                    self.output.write(i)
                    cid_counter += 1
                valid_counter += 1
            except (ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('%d logs related to %s' % (cid_counter, self.c_id))
        print ('%d logs are valid' % (valid_counter))
        print ('%d logs are invalid' % (invalid_counter))
        return cid_counter

    def parse_gzfile_cid(self):
        outfile = '../result/' + self.c_id + '_' + repr(self.start_date) + '_' + repr(self.end_date) + '.orig'
        self.output = open(outfile, 'w')

        counter = 0
        for i in self.filelist:
            counter += self.__parse_gzfile_cid_sub(i)
        print ('--------Total %d log data--------' % (counter))

        self.output.close()

    def __parse_gzfile_uid_date_sub(self, uid, filename):
        print ('parse ' + filename)
        invalid_counter = 0
        uid_counter = 0
        counter = 0
        for i in gzip.open(filename, 'rt'):
            counter += 1
            if counter % 100000 == 0:
                print (counter)
            try:
                content = json.loads(i, strict=False)
                user_id = content['context']['user_id']
                # get the log data related to a certain uid
                if user_id == uid:
                    self.output.write(i)
                    uid_counter += 1
            except (ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('%d logs related to %d' % (uid_counter, uid))
        return uid_counter

    def parse_gzfile_uid_date(self, uid, date):
        self.output = open('../result/uid_' + repr(uid) + '_date_' + repr(uid) + '.orig')
        uid_counter = 0
        for i in self.all_dirs:
            dirname = '/mnt/logs' + i + '/log/tracking/'
            filename = dirname + 'tracking.log-' + repr(date) + '.gz'
            uid_counter += self.__parse_gzfile_uid_date_sub(uid, filename)
        print ('--------Total %d log data--------' % (uid_counter))
        self.output.close()
        
    def gen_orig_filelist(self):
        self.filelist = list()
        rdir = '../result/'
        for i in os.listdir(rdir):
            if i.endswith('.orig') and i.startswith(self.c_id):
                self.filelist.append(rdir + i)

    def __parse_log_by_event_type_sub(self, filename):
        print ('parse' + filename)
        counter = 0

        video_counter = 0
        forum_counter = 0
        forum_view_counter = 0
        problem_counter = 0
        other_counter = 0
        invalid_counter = 0

        forum_view_pattern = re.compile(r'.*?/discussion/forum/.*?/threads/[0-9a-z]*')

        for i in open(filename):
            try:
                counter += 1
                if counter % 100000 == 0:
                    print (counter)

                content = json.loads(i, strict=False)
                event_type = content['event_type']
                # all the logs related to video
                # remove those without username or user_id
                # only need to save part of the original json data
                if event_type in self.video_type:
                    if content['username'] == '' or content['context']['user_id'] == '':
                        continue
                    newlog = {
                        'event_type' : content['event_type'],
                        'event' : content['event'],
                        'context' : content['context'],
                        'time' : content['time'],
                        'referer' : content['referer']
                    }
                    self.video_out.write(json.dumps(newlog) + '\n')
                    video_counter += 1
                # all the logs related to forum database change
                # this does not include viewing the forum only
                elif event_type in self.forum_type:
                    if content['username'] == '' or content['context']['user_id'] == '':
                        continue
                    newlog = {
                        'event_type' : content['event_type'],
                        'time' : content['time'],
                        'context' : content['context'],
                        'body' : content['event']['body'][:100],    # record at most 100 char of body
                        'id' : content['event']['id'],
                        'referer' : content['referer']
                    }
                    self.forum_out.write(json.dumps(newlog) + '\n')
                    forum_counter += 1
                elif event_type in self.problem_type:
                    if content['username'] == '' or content['context']['user_id'] == '':
                        continue
                    # only record the problem_check event that happened on server
                    if event_type == 'problem_check' and content['event_source'] == 'browser':
                        continue
                    newlog = {
                        'event_type' : content['event_type'],
                        'time' : content['time'],
                        'context' : content['context'],
                        'referer' : content['referer'],
                        'event' : content['event']
                    }
                    self.problem_out.write(json.dumps(newlog) + '\n')
                    problem_counter += 1
                # other logs related to forum, but not related to database change
                # entering a specific post, but only viewing
                elif forum_view_pattern.match(content['event_type']):
                    if content['username'] == '' or content['context']['user_id'] == '':
                        continue
                    newlog = {
                        'event_type' : 'view_forum',
                        'time' : content['time'],
                        'context' : content['context'],
                        'referer' : content['referer']
                    }
                    self.forum_view_out.write(json.dumps(newlog) + '\n')
                    forum_view_counter += 1
                # other logs, not related to this project
                else:
                    if content['username'] == '' or content['context']['user_id'] == '':
                        continue
                    self.other_out.write(i)
                    other_counter += 1
            except (ValueError, KeyError):
                self.invalid_out.write(i)
                invalid_counter += 1
                continue

        print ('%d logs related to video' % (video_counter))
        print ('%d logs related to forum' % (forum_counter))
        print ('%d logs related to forum view' % (forum_view_counter))
        print ('%d logs related to problem' % (problem_counter))
        print ('%d logs are others' % (other_counter))
        print ('%d logs are invalid' % (invalid_counter))
        return [video_counter, forum_counter, forum_view_counter, problem_counter, other_counter, invalid_counter]

    def parse_log_by_event_type(self):
        self.video_out = open('../result/' + self.c_id + '.video', 'w')
        self.forum_out = open('../result/' + self.c_id + '.forum', 'w')
        self.forum_view_out = open('../result/' + self.c_id + '.forum_view', 'w')
        self.problem_out = open('../result/' + self.c_id + '.problem', 'w')
        self.other_out = open('../result/' + self.c_id + '.other', 'w')
        self.invalid_out = open('../result/' + self.c_id + '.invalid', 'w')

        self.video_type = { 'play_video', 
                            'pause_video', 
                            'seek_video', 
                            'load_video_error',
                            'stop_video'}

        self.forum_type = { 'django_comment_client.base.views.vote_for_thread', 
                            'django_comment_client.base.views.vote_for_comment', 
                            'django_comment_client.base.views.update_comment',
                            'django_comment_client.base.views.create_comment'}
        '''
            The following log related to forum_type are not considered:
            {
                'django_comment_client.base.views.undo_vote_for_comment',
                'django_comment_client.base.views.follow_thread',
                'django_comment_client.base.views.pin_thread',
                'django_comment_client.base.views.openclose_thread',
                'django_comment_client.base.views.delete_comment'}
        '''

        self.problem_type = {   'showanswer',
                                'problem_save',
                                'problem_check',
                                'problem_graded'}
        '''
            The following log related to problem_type are not considered:
            {
                'problem_reset',
                'problem_get',
                'problem_show',
                'save_problem_success'}
        '''

        # video_counter, forum_counter, forum_view_counter, problem_counter, other_counter, invalid_counter
        counters = [0, 0, 0, 0, 0, 0]

        for i in self.filelist:
            templist = self.__parse_log_by_event_type_sub(i)
            for j in range(len(templist)):
                counters[j] += templist[j]

        print ('--------Total %d video log--------' % (counters[0]))
        print ('--------Total %d forum log--------' % (counters[1]))
        print ('--------Total %d forum view log--------' % (counters[2]))
        print ('--------Total %d problem log--------' % (counters[3]))
        print ('--------Total %d other log--------' % (counters[4]))
        print ('--------Total %d invalid log--------' % (counters[5]))

        self.video_out.close()
        self.forum_out.close()
        self.forum_view_out.close()
        self.problem_out.close()
        self.other_out.close()
        self.invalid_out.close()

    def check_event_type(self, filename):
        print ('checking the type of ' + filename)
        type_dict = dict()
        counter = 0
        invalid_counter = 0
        valid_counter = 0

        for i in open(filename, 'rt'):
            counter += 1
            if counter % 10000 == 0:
                print (counter)
            try:
                content = json.loads(i, strict=False)
                event_type = content['event_type']
                if event_type not in type_dict:
                    type_dict[event_type] = 0
                type_dict[event_type] += 1
                valid_counter += 1
            except ValueError:
                invalid_counter += 1
                continue
        type_list = sorted(type_dict.items(), key=lambda d:d[1], reverse=True)
        for i in type_list:
            print ('%d log data with type %s' % (i[1], i[0]) )
        print ('--------Total %d invalid log data--------' % (invalid_counter))
        print ('--------Total %d valid log data--------' % (valid_counter))
    
    def sort_log_by_timestamp(self, filename):
        print ('sorting ' + filename)
        invalid_counter = 0
        counter = 0
        log_dict = dict()
        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                time = content['time']
                log_dict[time + repr(hash(i))] = i
                counter += 1
                if counter % 100000 == 0:
                    print (counter)
            except (ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('%d independent log data in %d' % (len(log_dict), counter))
        print ('%d invalid log data' % (invalid_counter))

        sorted_list = sorted(list(log_dict))
        print ('saving to ' + filename + '.sorted')
        output = open(filename + '.sorted', 'w')
        for i in sorted_list:
            output.write(log_dict[i])
        output.close()
    
    def sort_all_log_files_by_timestamp(self):
        file_suffix = ['.forum', '.forum_view', '.invalid', '.problem', '.video']
        for i in file_suffix:
            self.sort_log_by_timestamp('../result/' + self.c_id + i)

    def __get_path(self, content):
        all_path = content['context']['path']
        temp = all_path[: all_path.rfind('/')]
        return temp[temp.rfind('/')+1 :]

    def __parse_referer(self, content):
        referer = content['referer']
        pos1 = referer.rfind('/', 0, -1)
        pos2 = referer.rfind('/', 0, pos1)
        return referer[pos2+1:pos1], referer[pos1+1:-1]

    def __parse_forum_by_structure_sub(self, forum_file, forum_dict):
        counter = 0
        invalid_counter = 0
        print ('parsing ' + forum_file)
        for i in open(forum_file):
            try:
                content = json.loads(i, strict=False)
                referer = content['referer']
                thread = referer[referer.rfind('/')+1 :]

                # use this to filter some jump link from other website
                # thread length filter
                if len(thread) != 24:
                    continue

                # create a new thread if needed
                if thread not in forum_dict:
                    forum_dict[thread] = {'view' : [], 'vote' : [], 'update' : [], 'comment' : {}}

                event_type = content['event_type']
                if event_type == 'view_forum':
                    forum_dict[thread]['view'].append(content)
                elif event_type == 'django_comment_client.base.views.vote_for_thread':
                    forum_dict[thread]['vote'].append(content)
                elif event_type == 'django_comment_client.base.views.vote_for_comment':
                    # you can not vote for a 2-level comment, so there is only one kind of vote for comment
                    path = self.__get_path(content)
                    if path in forum_dict[thread]['comment']:
                        forum_dict[thread]['comment'][path]['vote'].append(content)
                    # there is no such 1-level comment for you to vote
                    else:
                        print ('!!!Can not find forum, vote_for_comment!!!')
                        print (content['time'])
                elif event_type == 'django_comment_client.base.views.create_comment':
                    path = self.__get_path(content)
                    # path == thread, this is a 1-level comment under a certain thread
                    if path == thread:
                        comment_id = content['id']
                        forum_dict[thread]['comment'][comment_id] = content
                        forum_dict[thread]['comment'][comment_id]['comment'] = list()
                        forum_dict[thread]['comment'][comment_id]['vote'] = list()
                        forum_dict[thread]['comment'][comment_id]['update'] = list()
                    # path != thread, this is a comment under a certain comment
                    else:
                        if path in forum_dict[thread]['comment']:
                            forum_dict[thread]['comment'][path]['comment'].append(content)
                        # there is no such 1-level comment for you to add 2-level comment
                        else:
                            print ('!!!Can not find forum, create_comment!!!')
                            print (content['time'])
                elif event_type == 'django_comment_client.base.views.update_comment':
                    path = self.__get_path(content)
                    # if the update has a certain id, then update it under this id
                    if path in forum_dict[thread]['comment']:
                        forum_dict[thread]['comment'][path]['update'].append(content)
                    # if the update does not has a certain id, then update under thread
                    # this may be caused by update of a 2-level comment
                    else:
                        forum_dict[thread]['update'].append(content)
                counter += 1
            except (ValueError, KeyError):
                invalid_counter += 1
                continue
        return counter, invalid_counter

    def show_forum_structure(self, forum_dict):
        print ('--------Total %d threads are as followed--------' % (len(forum_dict)))
        for i in forum_dict:
            print ('!!!' + i + '!!!')
            view_count = len(forum_dict[i]['view'])
            unview_count = len(forum_dict[i]['vote']) + len(forum_dict[i]['update'])
            for j in forum_dict[i]['comment']:      # traverse all the comments
                unview_count += 1       # the comment itself
                unview_count += len(forum_dict[i]['comment'][j]['comment'])
                unview_count += len(forum_dict[i]['comment'][j]['update'])
                unview_count += len(forum_dict[i]['comment'][j]['vote'])
            print ('\t---%d unview, %d view log data---' % (unview_count, view_count))
        print ('--------All threads are shown--------')
    
    def parse_forum_by_structure(self):
        '''
            Parse the forum by structure
            Show which log is thread, which is comment, which is vote
        '''
        forum_dict = dict()
        counter = 0
        invalid_counter = 0

        filename = '../result/' + self.c_id + '.forum.sorted'
        c, ic = self.__parse_forum_by_structure_sub(filename, forum_dict)
        counter += c
        invalid_counter += ic
        filename = '../result/' + self.c_id + '.forum_view.sorted'
        c, ic = self.__parse_forum_by_structure_sub(filename, forum_dict)
        counter += c
        invalid_counter += ic
        
        print ('--------Total %d invalid data--------' % (invalid_counter))
        print (('--------Total %d valid data--------' % (counter)))
        
        self.show_forum_structure(forum_dict)

        output = open('../result/' + self.c_id + '.structured_forum', 'w')
        output.write(json.dumps(forum_dict) + '\n')
        output.close()

    def show_problem_structure(self, problem_dict):
        print ('--------Total %d threads' % (len(problem_dict)))
        for i in problem_dict:
            print ('!!!' + i + '!!!')
            s = 0
            for j in problem_dict[i]:
                li = problem_dict[i][j]
                sumlength = len(li['showanswer']) + len(li['problem_save']) + len(li['problem_check']) + len(li['problem_graded'])
                print ('\t---%s---   %d logs' % (j, sumlength) )
                s += sumlength
            print ('!!!Total %d logs!!!' % (s))
        print ('--------All threads are shown--------')

    def parse_problem_by_structure(self):
        '''
            Parse the questions by structure
            Show which part of questions belongs to each other
        '''
        problem_dict = dict()
        counter = 0
        invalid_counter = 0

        filename = '../result/' + self.c_id + '.problem.sorted'
        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                index1, index2 = self.__parse_referer(content)

                # use this to filter some actions from other sources, like mail.163 ...
                # this will filter about 1800 log data in 20740042X
                # thread length filter
                if len(index1) != 32 or len(index2) != 32:
                    continue

                # create new two levels of index
                if index1 not in problem_dict:
                    problem_dict[index1] = dict()
                if index2 not in problem_dict[index1]:
                    problem_dict[index1][index2] = {'showanswer' : [], 'problem_save' : [], 
                                                    'problem_check' : [], 'problem_graded' : []}

                event_type = content['event_type']
                problem_dict[index1][index2][event_type].append(content)
                counter += 1
            except (ValueError, KeyError):
                invalid_counter += 1
                continue

        print ('--------Total %d invalid data--------' % (invalid_counter))
        print (('--------Total %d valid data--------' % (counter)))

        self.show_problem_structure(problem_dict)

        output = open('../result/' + self.c_id + '.structured_problem', 'w')
        output.write(json.dumps(problem_dict) + '\n')
        output.close()

    def __calc_list_sum(self, timelist):
        '''
            A sub function called by compute video time
            Calculate the overlapping video time
        '''
        sum_time = overlap_time = 0
        timelist.sort()
        temp = [i[1] - i[0] for i in timelist]
        sum_time = sum(temp)

        start = 0
        for i in range(1, len(timelist)):
            if timelist[i][0] <= timelist[start][1]:
                if timelist[i][1] > timelist[start][1]:
                    timelist[start][1] = timelist[i][1]
                    timelist[i][1] = timelist[i][0]
                elif timelist[i][1] <= timelist[start][1]:
                    timelist[i][1] = timelist[i][0]
            elif timelist[i][0] > timelist[start][1]:
                start = i

        temp = [i[1] - i[0] for i in timelist]
        overlap_time = sum(temp)
        return sum_time, overlap_time

    def check_video_data_valid(self, video_user_date):
        '''
            check if the list is correct
            pop the last one if it is not finished
        '''
        invalid_video = open('../result/' + self.c_id + '.video_invalid', 'w')
        invalid_counter = 0
        video_counter = 0
        for vid in video_user_date:
            for uid in video_user_date[vid]:
                for date in video_user_date[vid][uid]:
                    video_counter += 1
                    try:
                        timelist = video_user_date[vid][uid][date]
                        if timelist[-1][1] == -1:
                            timelist.pop()
                        for i in timelist:
                            if i[0] > i[1]:
                                # if there is an invalid pair, this timelist will be recorded
                                # and we will delete the invalid pair
                                invalid_video.write('%s %s %s : ' % (vid, uid, date))
                                invalid_video.write(repr(timelist) + '\n')
                                invalid_counter += 1
                                templist = list()
                                for j in timelist:
                                    if i[0] <= i[1]:
                                        templist.append(i)
                                video_user_date[vid][uid][date] = templist
                                break
                    except (ValueError, TypeError):
                        print (timelist)
        invalid_video.close()
        print ('Total %d invalid video in %d video' % (invalid_counter, video_counter))

    def compute_video_time(self, video_user_date):
        ''' sort and compute sum time and overlap time for each video '''
        for vid in video_user_date:
            for uid in video_user_date[vid]:
                for date in video_user_date[vid][uid]:
                    timelist = video_user_date[vid][uid][date]
                    sum_time, overlap_time = self.__calc_list_sum(timelist)
                    video_user_date[vid][uid][date] = (sum_time, overlap_time)

    def show_video_structure(self, video_user_date, video_dict):
        video_time = dict()
        for vid in video_user_date:
            stime = 0
            otime = 0
            for uid in video_user_date[vid]:
                for date in video_user_date[vid][uid]:
                    stime += video_user_date[vid][uid][date][0]
                    otime += video_user_date[vid][uid][date][1]
            video_time[vid] = [stime, otime]
        lecture_time = dict()
        for id1 in video_dict:
            lecture_time[id1] = [0, 0]
            for id2 in video_dict[id1]:
                for vid in video_dict[id1][id2]:
                    lecture_time[id1][0] += video_time[vid][0]
                    lecture_time[id1][1] += video_time[vid][1]
        print ('--------Total %d lectures are as followed--------' % (len(lecture_time)))
        for i in lecture_time:
            print ('!!!%s!!!' % (i))
            print ('\t---%f sum time, %f overall time---' % (lecture_time[i][0], lecture_time[i][1]))
        print ('--------All lectures are shown--------')


    def debug_filter_by_event_type(self, filename, event_type):
        '''
            a debug function for all kinds of data
            given an event_type, get all related log data of this type
        '''
        output_file = '../result/' + self.c_id + '.type.' + event_type
        output = open(output_file, 'w')
        invalid_counter = 0
        valid_counter = 0
        counter = 0
        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                etype = content['event_type']
                if etype == event_type:
                    output.write(i)
                    valid_counter += 1
                counter += 1
                if counter % 100000 == 0:
                    print ('---%d log data---' % (counter))
            except(ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('--------Total %d invalid data--------' % (invalid_counter))
        print ('--------Get %d data--------' % (valid_counter))
        output.close()

    def video_debug_filter(self, vid, uid, date):
        '''
            a debug function for video log data
            given vid, uid and date, get all log data related to these three parameter
        '''
        filename = '../result/' + self.c_id + '.video.sorted'
        outfile = '../result/' + self.c_id + '_' + vid + '_' + repr(uid) + '_' + date
        output = open(outfile, 'w')
        invalid_counter = 0
        valid_counter = 0
        counter = 0
        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                cvid = content['event']['id']
                cuid = content['context']['user_id']
                cdate = content['time'][:10]
                if cvid == vid and cuid == uid and cdate == date:
                    output.write(i)
                    valid_counter += 1
                counter += 1
                if counter % 100000 == 0:
                    print ('---%d log data---' % (counter))
            except(ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('--------Total %d invalid data--------' % (invalid_counter))
        print ('--------Get %d data--------' % (valid_counter))
        output.close()

    def parse_video_by_structure(self):
        '''
            Parse the questions by structure
            Show which part of questions belongs to each other
        '''
        # video_dict represent the structure of all the videos
        # such as which video is under which thread
        video_dict = dict()

        # video_user_date represent how much time a video is watched 
        # by a certain user on a certain day
        video_user_date = dict()

        counter = 0
        invalid_counter = 0
    
        filename = '../result/' + self.c_id + '.video.sorted'
        vid_prefix = 'i4x-TsinghuaX-' + self.c_id + '-video-'

        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                index1, index2 = self.__parse_referer(content)
                vid = content['event']['id']

                # use this to filter some actions from other sources
                # thread length filter
                if len(index1) != 32 or len(index2) != 32:
                    continue
                if len(vid) != 62 or (not vid.startswith(vid_prefix)):
                    continue

                # build the structure part of video logs
                if index1 not in video_dict:
                    video_dict[index1] = dict()
                if index2 not in video_dict[index1]:
                    video_dict[index1][index2] = set()

                if vid not in video_dict[index1][index2]:
                    video_dict[index1][index2].add(vid)

                # build the user date part of video logs
                uid = content['context']['user_id']
                date = content['time'][:10]
                etype = content['event_type']
                if vid not in video_user_date:
                    video_user_date[vid] = dict()
                if uid not in video_user_date[vid]:
                    video_user_date[vid][uid] = dict()
                if date not in video_user_date[vid][uid]:
                    video_user_date[vid][uid][date] = [ [-1, -1] ]

                timelist = video_user_date[vid][uid][date]
                if etype == 'play_video':
                    if timelist[-1][0] == -1:
                        timelist[-1][0] = content['event']['currentTime']
                elif etype == 'pause_video':
                    if timelist[-1][0] != -1:
                        timelist[-1][1] = content['event']['currentTime']
                        timelist.append( [-1, -1] )
                elif etype == 'stop_video':
                    if timelist[-1][0] != -1:
                        timelist[-1][1] = content['event']['currentTime']
                        timelist.append( [-1, -1] )
                elif etype == 'seek_video':
                    # seek when the video is playing, if seek when the video is paused, then do nothing
                    # when seeking video, new_time or old_time can be null...
                    if content['event']['old_time'] == None or content['event']['new_time'] == None:
                        invalid_counter += 1
                        continue
                    if timelist[-1][0] != -1:
                        timelist[-1][1] = content['event']['old_time']
                        timelist.append( [content['event']['new_time'], -1] )
                elif etype == 'load_video_error':
                    if timelist[-1][0] != 0:
                        # sometimes, when load video error, currentTime = 0, which means nothing
                        if content['event']['currentTime'] != 0:
                            timelist[-1][1] = content['event']['currentTime']
                            timelist.append( [-1, -1] )
                counter += 1
                if counter % 100000 == 0:
                    print ('---%d log data---' % (counter))
            except (ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('--------Total %d invalid data--------' % (invalid_counter))
        print ('--------Total %d valid data--------' % (counter))

        # check valid of video data, and calculate overall time
        self.check_video_data_valid(video_user_date)
        self.compute_video_time(video_user_date)
        self.show_video_structure(video_user_date, video_dict)
        
        # dump to file
        for id1 in video_dict:
            for id2 in video_dict[id1]:
                video_dict[id1][id2] = list(video_dict[id1][id2])
        output_file = open('../result/' + self.c_id + '.structured_video', 'w')
        output_file.write(json.dumps(video_dict) + '\n')
        output_file.close()

        output_file = open('../result/' + self.c_id + '.video_time', 'w')
        output_file.write(json.dumps(video_user_date) + '\n')
        output_file.close()

    def get_course_structure_by_url(self, url):
        '''
            this function can not work...
            because you have to log in to see the details of a course
        '''
        fp = urllib.request.urlopen(url)
        webbytes = fp.read()
        webstring = webbytes.decode('utf-8')
        fp.close()

        outfile = '../result/' + self.c_id + '.course_structure'
        output = open(outfile, 'w', encoding='utf-8')
        output.write(webstring)
        output.close()

    def parse_course_structure(self):
        '''
            parse the course structure
            create a mapping from hash-code to course name
        '''
        # using the webpage downloaded directly from browser
        filename = '../result/' + self.c_id + '.html'
        if not os.path.exists(filename):
            print ('you need a webpage to introduce the course structure')
            print ('you should download it from the \'courseware\' page of your course')
            assert(False)
            
        # course_structure shows the structure of this course
        # course_mapping map the structure to the hash number
        course_structure = dict()
        course_mapping = dict()

        content = open(filename, 'r', encoding='utf-8').read()
        soup = BeautifulSoup(content, 'html.parser')
        related = soup.find_all('div', class_='chapter')
        for i in related:
            index1 = i.h3.a.string
            li = i.ul.find_all('p', class_='')
            href_li = i.ul.find_all('a')
            assert (len(li) == len(href_li))
            course_structure[index1] = [i.string for i in li]
            single_index = set()
            for it in range(len(li)):
                referer = href_li[it].attrs['href']
                pos1 = referer.rfind('/', 0, -1)
                pos2 = referer.rfind('/', 0, pos1)
                id1, id2 = referer[pos2+1:pos1], referer[pos1+1:-1]
                assert (len(id1) == 32)
                assert (len(id2) == 32)
                single_index.add(id1)
                course_mapping[id2] = li[it].string
            assert (len(single_index) == 1)

        outfile = '../result/' + self.c_id + '.course_structure'
        output = open(outfile, 'w', encoding='utf-8')
        output.write(json.dumps(course_structure, ensure_ascii=False) + '\n')
        output.write(json.dumps(course_mapping, ensure_ascii=False) + '\n')
        output.close()

    def load_course_structure(self):
        ''' load the course structure and mapping from file'''
        filename = '../result/' + self.c_id + '.course_structure'

        course_structure = dict()
        course_mapping = dict()

        file_handle = open(filename, 'r', encoding='utf-8')
        try:
            content = file_handle.readline()
            course_structure = json.loads(content, strict=False)
            content = file_handle.readline()
            course_mapping = json.loads(content, strict=False)
        except (ValueError, KeyError):
            print ('load course structure error')
        return course_structure, course_mapping

    def files_check(self):
        ''' 
            check if all files required are generated
            check if we can delete some useless files
        '''
        file_suffix = [ '.structured_forum', '.structured_problem', 'structured_video',
                        '.video_time', '.course_structure', '.html']
        # check if there are files that are required but not exist
        fileset = set(os.listdir('../result/'))
        for i in file_suffix:
            if (self.c_id + i) not in fileset:
                print (self.c_id + i + ' does not exist')
                assert(False)

        # check if there are files that are useless and can be deleted
        delete_file_suffix = ['.forum', '.forum_view', '.invalid', '.problem', '.video']
        for i in delete_file_suffix:
            if (self.c_id + i) in fileset:
                print ('delete useless file: ' + self.c_id + i)
                os.remove('../result/' + self.c_id + i)

    def run_on_server(self):
        '''
            this function should run on the data server
            there are some path related to the data server, like edxdbweb1
        '''
        self.gen_gzfilelist()
        self.parse_gzfile_cid()
        # this function will generate a file in ../result/
        # you can copy this file to a local computer

    def run_on_local_computer(self):
        '''
            this function can run on data server or local computer
        '''
        # parse the course structure
        self.parse_course_structure()

        # parse log data and sort them
        self.gen_orig_filelist()
        self.parse_log_by_event_type()
        self.sort_all_log_files_by_timestamp()

        # parse three kinds of log data
        self.parse_problem_by_structure()
        self.parse_forum_by_structure()
        self.parse_video_by_structure()

        self.files_check()
        # data preparation ends here

    def test(self):
        #self.parse_course_structure()
        #self.parse_forum_by_structure()
        #self.parse_problem_by_structure()
        self.parse_video_by_structure()
        #self.video_debug_filter('i4x-TsinghuaX-20740042X-video-a18cba64ddbe459a9897c070a3f04adf', 161855, '2015-10-28')
        #self.debug_filter_by_event_type('../result/20740042X.video.sorted', 'load_video_error') 

def main():
    f = Filter(20150906, 20151231, '20740042X')
    f.test()

if __name__ == '__main__':
    main()

'''
    RESULT 2016/01/17
    --------Total 882090 video log--------
    --------Total 1851 forum log--------
    --------Total 15999 forum view log--------
    --------Total 46427 problem log--------
    --------Total 1822996 other log--------
    --------Total 168 invalid log--------
'''

'''
    视频行为具体怎么分析
    导学帖子，类似html的一个课程封面
'''