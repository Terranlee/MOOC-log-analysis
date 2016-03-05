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
    
def main():
    a = Analyzer('20740042X')


if __name__ == '__main__':
    main()