from random import randint
cost = 76 * 10
arr = [1020, 840] #- не долбимся с флоатом
#arr = [1050, 870]  #- активно долбимся с продажей и флоатом
percent = [0.5, 0.5]
percentrise = [0]
for i in range(len(percent)):
    percentrise.append(percentrise[-1] + percent[i] * 100 )

com = 0.87
it = 10
atts = 100000
fail = 0
start = 1800
midans = 0
for k in range(atts):
    ans = start
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

print("Шанс додепа: ", fail / (it * atts) * 100, "%", sep = "")
print("Стоимость инпутов:", cost)
print("Средний профит за трейд:", (midans / atts - start) / it)
'''
Вывод следующий:
Проще свести трейд к 100%
'''