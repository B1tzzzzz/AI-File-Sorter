from subprocess import Popen, PIPE
import random as r
from numba import njit

def generateTest():
    file = open("test.txt", "w")
    

def testing(it):
    for i in range(it):
        arr = generateTest()
        n = arr[0]
        m = arr[1]
        file = open('test.txt', 'r')    
        data = file.read()
        
        data = data.encode()
        p1 = Popen(["stupid.exe"], stdout=PIPE, stdin=PIPE)
        result1 = p1.communicate(input = data)
        decResult1 = result1[0].decode()
        ans = list(map(int, decResult1.split()))
        if (ans[0] != -1 and (ans[0] >= ans[1] or n % ans[0] != m % ans[1] or ans[1] % ans[0] != 0)):
            print("Failed test: ")
            print(data.decode())
            print(decResult1)
            break
            

if (__name__ == "__main__"):
    testing(100000)