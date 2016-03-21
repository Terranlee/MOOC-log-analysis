
import json

class UID2Name(object):
    """generate a mapping from UID to name"""
    def __init__(self, cid):
        super(UID2Name, self).__init__()
        self.result_dir = '../result/'
        self.c_id = cid
    
    def generate_by_file(self, filename):
        counter = 0

        username_set = set()
        uid_set = set()
        mapping = dict()

        for i in open(filename):
            try:
                counter += 1
                if counter % 100000 == 0:
                    print (counter)
                content = json.loads(i, strict=False)
                username = content['username']
                uid = content['context']['user_id']
                if uid == '' or username == '':
                    continue
                uid_set.add(uid)
                username_set.add(username)
                mapping[uid] = username
            except(ValueError, KeyError):
                continue

        print ('%d username captured' % (len(username_set)))
        print ('%d uid captured' % (len(uid_set)))

        outfile = self.result_dir + self.c_id + '.namemap'
        output = open(outfile, 'w')
        output.write(json.dumps(mapping) + '\n')
        output.close()

def main():
    un = UID2Name('20740042X')
    un.generate_by_file('../result/20740042X_20150906_20151231.orig')
    
if __name__ == '__main__':
    main()
    