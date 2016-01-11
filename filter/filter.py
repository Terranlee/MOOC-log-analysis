# Filter for xuetangX log data
import os
import json
import gzip

class Filter(object):
    '''docstring for Filter
        This is a filter for log data from xuetangX.
        Use this to get all the data from a specific course.
    '''

    def __init__(self, s_date, e_date):
        super(Filter, self).__init__()
        # start_date and end_date are numbers like 20150715
        self.start_date = s_date
        self.end_date = e_date

        self.filelist = list()
        self.__gen_filelist()

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

    def __parse_gzfile_sub(self, filename):
        print ('parse' + filename)
        for i in gzip.open(filename, 'rt'):
            self.__parse_log(i)

    def parse_gzfile(self):
        for i in self.filelist:
            self.__parse_gzfile_sub(i)

    def test(self):
        pass

def main():
    f = Filter(20151201, 20151231)
    f.gen_filelist()
    f.parse_gzfile()

if __name__ == '__main__':
    main()

