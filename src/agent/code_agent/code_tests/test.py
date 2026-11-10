from random import randint
cost = 79*10
#cost = 79 * 9 + 25.3
arr = [505, 1160, 450, 1050, 800]
arr = [800, 1050]
#arr = [505, 350, 450, 1050, 800]
#arr = [520, 1200, 460, 1100, 870]
percent = [0.5, 0.5]
percentrise = [0]
for i in range(len(percent)):
    percentrise.append(percentrise[-1] + percent[i] * 100 )

com = 0.87
it = 10
atts = 100000
fail = 0
midans = 0
for k in range(atts):
    ans = 1500
    for i in range(it):
        rnd = randint(0, 100)
        idx = 0
        for j in range(len(percentrise)):
            if rnd < percentrise[j]:
                idx = j - 1
                break 
            
        ans += arr[idx] * com - cost
        if (ans < cost):
            fail += 1
            break

    midans += ans

print(fail)
print(fail / (it * atts) * 100, "%", sep = "")
print(midans / 100000)