from datetime import datetime
now = datetime.now()
competitor = []
no = 1
i = 0
num = int(input('\nplease input number of competitors : '))

#receive data
for i in range(num) :
    name = input("\nplease competitor's name : ")
    time = float(input('please input time : '))
    points = int(input('please input points : '))
    competitor.append([name,time,points])

#hit factor
for p in competitor :
    p.append(p[2]/p[1]) #hf = points / time

max_hf = max(p[3] for p in competitor) 
max_points = max(p[2] for p in competitor)
    #use max to find a max value of hf 

for p in competitor :
    state_point = (p[3] / max_hf)*max_points
    state_percent = (state_point / max_points)*100
    p.append(state_point)
    p.append(state_percent)

#sort data
competitor.sort(key = lambda x:x[5] , reverse = True) 
    #use lambda to sort data / return = true for sorting maximum to minimum
    #x[5] is sorting data from index 5 (idx 5 is state percent)

#show result
print('\nShotgun Training 2025\nCondition : 1')    
print('Date and Time : ',now.strftime('%d/%m/%Y  %H:%M:%S')) #date and time
print('{0:=<120}'.format(''))
print('{0:<5}{1:<9}{2:<13}{3:<17}{4:<15}{5:<20}{6:<20}'.format('No.', 'PTS', 'TIME', 'COMPETITOR', 'HF', 'STATE POINTS', 'STATE PERCENT'))
print('{0:=<120}'.format(''))
for c in competitor :
    print('{0:<5}{1:<9}{2:<13}{3:<17}{4:<15.4f}{5:<20.2f}{6:<20.2f}'.format(no,c[2],c[1],c[0],c[3],c[4],c[5]))
    no += 1