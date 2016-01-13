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

        outfile = '../result/' + repr(cid) + '_' + repr(s_date) + '_' + repr(e_date) + '.orig'
        self.output = open(outfile, 'w')

        self.filelist = list()

    def __del__(self):
        self.output.close()

    def __gen_filelist_sub(self, rdir):
        for i in os.listdir(rdir):
            if i.endswith('.gz') and i.startswith('tracking.log-'):
                date = i[13:21]
                if date >= self.start_date and date <= self.end_date:
                    self.filelist.append(rdir + i)

    def gen_filelist(self):
        all_dirs = ['edxdbweb1', 'edxdbweb2', 'edxdbweb5', 'edxdbweb6']
        for i in all_dirs:
            self.__gen_filelist_sub('/mnt/logs/' + i + '/log/tracking/')
        print ('Total %d files' % (len(self.filelist)))

    def __parse_gzfile_cid_sub(self, filename):
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
                    self.output.write(json.dumps(newlog) + '\n')
                    cid_counter += 1
                valid_counter += 1
            except ValueError:
                invalid_counter += 1
                continue
        print ('%d logs related to %s' % (cid_counter, self.c_id))
        print ('%d logs are valid' % (valid_counter))
        print ('%d logs are invalid' % (invalid_counter))
        return cid_counter

    def parse_gzfile_cid(self):
        counter = 0
        for i in self.filelist:
            counter += self.__parse_gzfile_cid_sub(i)
        print ()

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

def main():
    f = Filter(20151201, 20151231, '20740042X')
    #f.gen_filelist()
    #f.parse_gzfile()
    f.test()

if __name__ == '__main__':
    main()

