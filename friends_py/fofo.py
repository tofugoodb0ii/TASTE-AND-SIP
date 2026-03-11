print("Shotgun Training 2025")
import time
print(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()))
shotgun = []
def main():
    i = 1
    num = int(input("จำนวนผู้เข้าแข่งขัน ==> "))
    while i <= num:
        shoter = []
        print(f'คนที่ {i}')
        name = (input("ชื่อผู้เข้าแข่งขัน ==> "))
        points = int(input("คะแนนที่ได้ ==> "))
        time = float(input("เวลาที่ได้ ==> "))
        shoter.append(name)
        shoter.append(points) 
        shoter.append(time)
        shotgun.append(shoter)  
        i += 1
def show():
    data = [] #ลิสต์ใหม่รอรับค่าที่จะคำนวณ 
    for n, p, t in shotgun:
        hit = p / t #หา hit factor
        data.append([n, p, t, hit]) #เพิ่มข้อมูลที่ผู้ใช้งานกรอก n คือ ชื่อ , p คือ คะแนน ,t คือ เวลา แล้วก็ hit คือ hit factor ของแต่ละคน
    max_hf = max(row[3] for row in data) #idx 3 คือ hit (hit factor) หาค่าที่มากที่สุด max
    max_points = max(row[1] for row in data) #idx 1 คือ p (points) หาคา่ที่มากที่สุดด้วย max
    for row in data:
        hit = row[3] #idx 3 คือ hit (hit factor)
        state_point = (hit / max_hf) * max_points #max hf จากบรรทัดที่ 24
        state_percent = (state_point / max_points) * 100
        row.append(state_point)
        row.append(state_percent)
    data.sort(key=lambda x: x[5], reverse=True)
    print('{0:-<100}'.format(""))
    print('{0:<10}{1:<10}{2:<10}{3:<15}{4:<20}{5:25}{6:20}'.format(
        'No','Shoter','Point','Time','Hit Factory','Total Score','Score %'))
    print('{0:-<100}'.format(""))
    for idx, (n, p, t, hit, sp, spp) in enumerate(data, start=1):
        print('{0:<10}{1:<12}{2:<9}{3:<18}{4:<10.2f}{5:<12.2f}{6:25.2f}%'.format(idx, n, p, t, hit, sp, spp))
main()
show()