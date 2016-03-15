import random

def main():
    li = list()
    for i in range(4):
        temp = list()
        for j in range(4):
            temp.append(random.choice('abcdefghijklmnopqrstuvwxyz'))
        li.append(''.join(temp))
    print ("\"top\":" + repr(li))

if __name__ == '__main__':
    main()