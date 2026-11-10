from subprocess import Popen, PIPE
from random import randint

def generateTest():
    file = open("test.txt", "w")
    n = randint(1, 15)
    file.write(f'{n}\n')
    a = [[randint(1, 100) for i in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                a[i][j] = 0
            if i > j:
                a[i][j] = a[j][i]

            file.write(f'{a[i][j]} ')
        file.write('\n')
    file.close()
    return a

def check(ans, m):
    ans = ans.split('\n')
    getw = int(ans[0])
    if len(ans) == 1:
        return True
    path = list(map(lambda x: int(x), ans[1].split(' ')[:-1]))
    n = len(path)
    w = 0
    for i in range(1, n):
        w += m[path[i] - 1][path[i - 1] - 1]

    #print(w, getw)
    return w == getw
def testing(it):
    for i in range(it):
        matrix = generateTest()
        file = open('test.txt', 'r')    
        data = file.read()
        data = data.encode()
        p1 = Popen(["stupid.exe"], stdout=PIPE, stdin=PIPE)
        result1 = p1.communicate(input = data)
        decResult1 = result1[0].decode()
        
        if (not check(decResult1, matrix)):
            print("Failed test: ")
            print(data.decode())
            print(decResult1)
            break

if (__name__ == "__main__"):
    testing(10000)