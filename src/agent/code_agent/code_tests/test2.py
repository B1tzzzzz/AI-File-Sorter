from random import randint
cost = 81 * 9 + 25.3
#cost = 79 * 9 + 25.3
arr = [505, 1160, 450, 1050, 800]
#arr = [505, 350, 450, 1050, 800] - не долбимся с флоатом
#arr = [520, 1200, 460, 1100, 870] - активно долбимся с продажей и флоатом
percent = [0.0333333, 0.0333333, 0.0333333, 0.45, 0.45]
percentrise = [0]
for i in range(len(percent)):
    percentrise.append(percentrise[-1] + percent[i] * 100 )

com = 0.87
it = 10
atts = 100000
fail = 0
start = 1500
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
#1 трейд в среднем +60 рублей в оптимальном случае
#+10 рублей в худшем случае
#если не долбиться с флоатами то профит +22 рубля ;(