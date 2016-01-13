# Filter for xuetangX log data
# 20740042X
import os
import json
import gzip

class Filter(object):
    '''docstring for Filter
        This is a filter for log data from xuetangX.
        Use this to get all the data from a specific course.
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
                if date >= self.start_date and date <= self.end_date:
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
                # only record log data from the browser, not server
                if cid.find(self.c_id) != -1 and content['event_source'] == 'browser':
                    newlog = dict()
                    newlog['username'] = content['username']
                    newlog['event_type'] = content['event_type']
                    newlog['context'] = content['context']
                    newlog['referer'] = content['referer']
                    newlog['event'] = content['event']
                    newlog['time'] = content['time']
                    self.output.write(json.dumps(newlog) + '\n')
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
        video_counter = 0
        analytic_counter = 0
        invalid_counter = 0
        for i in open(filename):
            try:
                content = json.loads(i, strict=False)
                event_type = content['event_type']
                if event_type in self.video_type:
                    self.video_out.write(i + '\n')
                    video_counter += 1
                else if event_type in self.analytic_type:
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

        self.video_type = {'play_video', 'pause_video'}
        self.analytic_type = {'/analytic_track/i', '/analytic_track/p', '/analytic_track/t'}

        video_counter = 0
        analytic_counter = 0
        for i in self.filelist:
            (video_counter, analytic_counter) += self.__parse_log_by_event_type_sub(i)
        print ('--------Total %d video log--------' % (video_counter))
        print ('--------Total %d analytic log--------' % (analytic_counter))

        self.video_out.close()
        self.analytic_out.close()

    def parse_video_time_by_user(self):
        filename = '../result/' + self.c_id + '.video'
        invalid_counter = 0
        # key of this dict is (user_id + video_id)
        # value of this dict is the start time of this video
        # when we meet the pause_video, we aggregate the time of this video
        user_video_time = dict()
        for i in filename:
            try:
                content = json.loads(i, strict=False)
                uname = content['username']
                uid = content['context']['user_id']
                if uname == '' or uid == '':
                    invalid_counter += 1
                    continue

                if uid not in user_video_time:
                    user_video_time[uid] = {}

                date = content['time'][:10]
                if date not in user_video_time[uid]:
                    user_video_time[uid][date] = {}
                
            except (ValueError, KeyError):
                invalid_counter += 1
                continue

    def test(self):
        '''
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
                if content['event_source'] == 'server':
                    continue
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

def main():
    f = Filter(20151201, 20151231, '20740042X')
    #f.gen_gzfilelist()
    #f.parse_gzfile_cid()
    f.test()

if __name__ == '__main__':
    main()

