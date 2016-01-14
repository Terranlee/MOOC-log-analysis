# Filter for xuetangX log data
# 20740042X
import os
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

        self.filelist = list()

    def __gen_gzfilelist_sub(self, rdir):
        for i in os.listdir(rdir):
            if i.endswith('.gz') and i.startswith('tracking.log-'):
                date = i[13:21]
                if date >= repr(self.start_date) and date <= repr(self.end_date):
                    self.filelist.append(rdir + i)

    def gen_gzfilelist(self):
        all_dirs = ['edxdbweb1', 'edxdbweb2', 'edxdbweb5', 'edxdbweb6']
        for i in all_dirs:
            self.__gen_gzfilelist_sub('/mnt/logs/' + i + '/log/tracking/')
        print ('Total %d files' % (len(self.filelist)))

    def __parse_gzfile_cid_sub(self, filename):
        # get the log data with a certain CID
        print ('parse' + filename)
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
                    self.output.write(i + '\n')
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

    def gen_orig_filelist(self):
        self.filelist = list()
        for i in os.listdir('../result/'):
            if i.endswith('.orig') and i.startswith(self.cid):
                self.filelist.append(i)

    def __parse_log_by_event_type_sub(self, filename):
        print ('parse' + filename)
        counter = 0
        video_counter = 0
        analytic_counter = 0
        invalid_counter = 0
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
                        'time' : content['time']
                    }
                    self.video_out.write(json.dumps(newlog) + '\n')
                    video_counter += 1
                elif event_type in self.analytic_type:
                    self.analytic_out.write(i + '\n')
                    analytic_counter += 1
            except (ValueError, KeyError):
                invalid_counter += 1
                continue
        print ('%d logs related to video' % (video_counter))
        print ('%d logs related to analytic' % (analytic_counter))
        print ('%d logs are invalid' % (invalid_counter))
        return (video_counter, analytic_counter)

    def parse_log_by_event_type(self):
        self.video_out = '../result/' + self.c_id + '.video'
        self.analytic_out = '../result/' + self.c_id + '.analytic'

        self.video_type = {'play_video', 'pause_video', 'seek_video', 'load_video_error'}
        self.analytic_type = {'/analytic_track/i', '/analytic_track/p', '/analytic_track/t'}

        video_counter = 0
        analytic_counter = 0
        #for i in self.filelist:
            #(video_counter, analytic_counter) += self.__parse_log_by_event_type_sub(i)
        print ('--------Total %d video log--------' % (video_counter))
        print ('--------Total %d analytic log--------' % (analytic_counter))

        self.video_out.close()
        self.analytic_out.close()

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
                if etype == 'pause_video':
                    if timelist[-1][0] != -1:
                        timelist[-1][1] = content['event']['currentTime']
                        timelist.append( [-1, -1] )
                if etype == 'seek_video':
                    # seek when the video is playing
                    # if seek when the video is paused, do nothing
                    if timelist[-1][0] != -1:
                        timelist[-1][1] = content['event']['old_time']
                        timelist.append( [content['event']['new_time'], -1] )
                if etype == 'load_video_error':
                    if timelist[-1][0] != 0:
                        timelist[-1][1] = content['event']['currentTime']
                        timelist.append( [-1, -1] )
            except (ValueError, KeyError):
                invalid_counter += 1
                continue

        # check if the list is correct
        # pop the last one if it is not finished
        invalid_counter = 0
        invalid_video = open('../result/' + self.c_id + '.ivid', 'w')
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
        output_file = open('../result/' + c_id + '.vid_time', 'w')
        output_file.write(json.dumps(user_video_time) + '\n')
        output_file.close()

    def test(self):
        type_set = set()
        invalid_count = 0
        valid_count = 0
        counter = 0
        for i in open('../data/tracking.log-20151215.data', 'rt'):
            counter += 1
            if counter % 10000 == 0:
                print (counter)
            try:
                content = json.loads(i, strict=False)
                type_set.add(content['event_type'])
                valid_count += 1
            except ValueError:
                invalid_count += 1
                continue
        type_list = list(type_set)
        type_list.sort()
        for i in type_list:
            print (i)
        print (invalid_count)
        print (valid_count)
        '''
        self.filelist.append('../data/tracking.log-20151215.gz')
        self.parse_gzfile_cid()
        '''
def main():
    f = Filter(20150906, 20151231, '20740042X')
    #f.gen_gzfilelist()
    #f.parse_gzfile_cid()
    f.test()

if __name__ == '__main__':
    main()

