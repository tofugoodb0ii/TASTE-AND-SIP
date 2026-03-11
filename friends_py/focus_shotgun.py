print("Shotgun Training 2025")
import time
print(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()))
shotgun=[]
def main():
    i=1
    num=int(input("จำนวนผู้เข้าแข่งขัน ==> "))
    while i<=num:
        shoter=[]
        print(f'คนที่ {i}')
        name=(input("ชื่อผู้เข้าแข่งขัน ==> "))
        points=int(input("คะแนนที่ได้ ==> "))
        time=float(input("เวลาที่ได้ ==> "))
        shoter.append(name)
        shoter.append(points)
        shoter.append(time)
        shotgun.append(shoter)
        i+=1
def show():
    data=[]
    max_score=100
    for n,p,t in shotgun:
        hit=p/t  #ค่าคะแนนต่อเวลา
        data.append([n, p, t, hit])
    data.sort(key=lambda x: (-x[3], -x[1], x[2]))
    top_hit = data[0][3] if data else 0
    print('{0:-<100}'.format(""))
    print('{0:<10}{1:<10}{2:<10}{3:<15}{4:<20}{5:25}{6:20}'.format('No','Shoter','Point','Time','Hit Factory','Total Score','Score %'))
    print('{0:-<100}'.format(""))
    for idx, (n, p, t, hit) in enumerate(data, start=1):
        perstat = (hit / top_hit * 100)
        total=(hit/(max(hit)))*max(p)
        print('{0:<10}{1:<12}{2:<9}{3:<18}{4:<10.2f}{5:12}{6:25.2f}%'.format(idx,n,p,t,hit,total,perstat))
main()
show()