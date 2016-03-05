#-*- coding: utf-8 -*-

# Analysis different kinds of log data
# cid : 20740042X
# uid : 502819
import json

class Analyzer(object):
    """docstring for Analyzer"""
    def __init__(self, cid):
        super(Analyzer, self).__init__()
        self.result_dir = '../result/'
        self.c_id = cid
        self.event_param = {
            'watch_video': 0.0,
            'django_comment_client.base.views.vote_for_thread': 0.0,
            'django_comment_client.base.views.vote_for_comment': 0.0, 
            'django_comment_client.base.views.update_comment': 0.0,
            'django_comment_client.base.views.create_comment': 0.0,
            'showanswer': 0.0,
            'problem_save': 0.0,
            'problem_check': 0.0,
            'problem_graded': 0.0
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

    def 
def main():
    a = Analyzer('20740042X')


if __name__ == '__main__':
    main()