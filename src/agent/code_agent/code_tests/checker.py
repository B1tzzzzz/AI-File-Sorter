from subprocess import Popen, PIPE
from random import randint

def generateTest():
    file = open("test.txt", "w")
    n = 2
    m = randint(1, 100000)
    file.write(f'{n} {m}\n{randint(1, 24)} {randint(1, 24)}')
    file.close()

def testing(it):
    for i in range(it):
        generateTest()
        file = open('test.txt', 'r')    
        data = file.read()

        data = data.encode()
        p1 = Popen(["stupid.exe"], stdout=PIPE, stdin=PIPE)
        p2 = Popen(["smart.exe"], stdout=PIPE, stdin=PIPE)
        result1 = p1.communicate(input = data)
        result2 = p2.communicate(input = data)
        decResult1 = result1[0].decode()
        decResult2 = result2[0].decode()
        
        if (decResult1 != decResult2):
            print("Failed test: ")
            print(data.decode())
            print(decResult1)
            print(decResult2)
            break

if (__name__ == "__main__"):
    testing(10000)

