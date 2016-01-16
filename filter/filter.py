# Filter for xuetangX log data
# cid : 20740042X
# uid : 502819
import os
import re
import json
import gzip

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
        # get the log data with a certain CID
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
            print (i)
        print (invalid_counter)
        print (valid_counter)
        
    def calc_list_sum(self, timelist):
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

    def parse_video_time_by_user(self):
        filename = '../result/' + self.c_id + '.video'
        invalid_counter = 0
        # key of this dict is (user_id + video_id)
        # value of this dict is the start time of this video
        # when we meet the pause_video, we aggregate the time of this video
        user_video_time = dict()
        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                uid = content['context']['user_id']
                if uid not in user_video_time:
                    user_video_time[uid] = {}
                date = content['time'][:10]
                if date not in user_video_time[uid]:
                    user_video_time[uid][date] = {}
                vid = content['event']['id']
                if vid not in user_video_time[uid][date]:
                    user_video_time[uid][date][vid] = [ [-1, -1] ]

                timelist = user_video_time[uid][date][vid]
                etype = content['event_type']
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
                    # seek when the video is playing
                    # if seek when the video is paused, do nothing
                    if timelist[-1][0] != -1:
                        timelist[-1][1] = content['event']['old_time']
                        timelist.append( [content['event']['new_time'], -1] )
                elif etype == 'load_video_error':
                    if timelist[-1][0] != 0:
                        timelist[-1][1] = content['event']['currentTime']
                        timelist.append( [-1, -1] )
            except (ValueError, KeyError):
                invalid_counter += 1
                continue

        # check if the list is correct
        # pop the last one if it is not finished
        invalid_counter = 0
        invalid_video = open('../result/' + self.c_id + '.video_invalid', 'w')
        for user in user_video_time:
            for date in user_video_time[user]:
                for video in user_video_time[user][date]:
                    timelist = user_video_time[user][date][video]
                    if timelist[-1][1] == -1:
                        timelist.pop()
                    for i in timelist:
                        if i[1] < i[0]:
                            invalid_counter += 1
                            invalid_video.write('%s %s %s : ' % (user, date, video))
                            invalid_video.write(repr(timelist) + '\n')
                            del( user_video_time[user][date][video] )
        print ('Total %d invalid video' % (invalid_counter))
        invalid_video.close()

        # sort and compute video time
        for user in user_video_time:
            for date in user_video_time[user]:
                for video in user_video_time[user][date]:
                    timelist = user_video_time[user][date][video]
                    sum_time, overlap_time = self.calc_list_sum(timelist)
                    user_video_time[user][date][video] = (sum_time, overlap_time)

        # save the dict to json
        output_file = open('../result/' + c_id + '.video_time', 'w')
        output_file.write(json.dumps(user_video_time) + '\n')
        output_file.close()

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

        print ('%d not same in %d' % (len(log_dict), counter))
        print ('%d invalid log data' % (invalid_counter))

        sorted_list = sorted(list(log_dict))
        print ('saving to ' + filename + '.sorted')
        output = open(filename + '.sorted', 'w')
        for i in sorted_list:
            output.write(log_dict[i])
        output.close()

    def test(self):
        type_set = set()
        invalid_counter = 0
        valid_counter = 0
        counter = 0
        for i in open('../data/tracking.log-20151215.data', 'rt'):
            counter += 1
            if counter % 10000 == 0:
                print (counter)
            try:
                content = json.loads(i, strict=False)
                type_set.add(content['event_type'])
                valid_counter += 1
            except ValueError:
                invalid_counter += 1
                continue
        type_list = list(type_set)
        type_list.sort()
        for i in type_list:
            print (i)
        print (invalid_counter)
        print (valid_counter)
        '''
        self.filelist.append('../data/tracking.log-20151215.gz')
        self.parse_gzfile_cid()
        '''

def main():
    f = Filter(20150906, 20151231, '20740042X')
    #f.gen_gzfilelist()
    #f.parse_gzfile_cid()
    #f.gen_orig_filelist()
    #f.parse_log_by_event_type()
    #f.sort_log_by_timestamp('../result/20740042X.invalid')

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