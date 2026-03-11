from datetime import datetime
now = datetime.now()
competitor = []
no = 1

num = int(input('please input number : '))

# --------------------------
# รับข้อมูลผู้แข่งขัน
# --------------------------
for i in range(num):
    name = input("please competitor's name : ")
    time = float(input('please input time : '))
    points = int(input('please input points : '))
    competitor.append([name, time, points])

# --------------------------
# คำนวณ Hit Factor, State Points, State Percent
# --------------------------
# หา hit factor ของแต่ละคน
for c in competitor:
    hit_factor = c[2] / c[1] if c[1] > 0 else 0
    c.append(hit_factor)  # index 3 = hit factor

# หา hit factor สูงสุด
max_hit_factor = max(c[3] for c in competitor)

# กำหนดคะแนนสูงสุด (ตามสนาม)
max_points = max(c[2] for c in competitor)

# คำนวณ state points และ state percent
for c in competitor:
    state_points = (c[3] / max_hit_factor) * max_points if max_hit_factor > 0 else 0
    state_percent = (state_points / max_points) * 100 if max_points > 0 else 0
    c.append(state_points)   # index 4 = state points
    c.append(state_percent)  # index 5 = state percent

# --------------------------
# เรียงลำดับจาก state percent สูงสุด → ต่ำสุด
# --------------------------
competitor.sort(key=lambda x: x[5], reverse=True)


print('Shotgun Sunday Training 2021\nCondition : 1')    
print('Date and Time : ', now.strftime('%d/%m/%Y  %H:%M:%S')) # date and time
print('\n{0:=<120}'.format(''))
print('{0:<5}{1:<9}{2:<13}{3:<17}{4:<25}{5:<30}{6:<35}'.format('No.', 'PTS', 'TIME', 'COMPETITOR', 'HIT FACTOR', 'STATE POINTS', 'STATE PERCENT'))
print('{0:=<120}'.format(''))

for i, x in enumerate(competitor, start=1):
    print('{0:<5}{1:<9}{2:<13}{3:<17}{4:<25.4f}{5:<30.4f}{6:<35.2f}'.format(i, x[2], x[1], x[0], x[3], x[4], x[5]))