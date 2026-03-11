#break assign number
#i = 1
#z = 2
#while(i < 13) :
#    print(str(z) + 'x' + str(i) + '=' + str(z*i) )
#    if i == 5 :
#        break
#    i += 1

#break input number
#i = 1
#z = int(input('pls input number :'))
#while(i < 13) :
#   print(str(z) + 'x' + str(i) + '=' + str(z*i) )
#   if i == 5 :
##   i += 1

#continue input number
#i = 1
#z = int(input('pls input number : '))
#while(i < 13) :
#    print(str(z) + 'x' + str(i) + '=' + str(z*i) )
#    if i == 5 :
#        continue
#    i += 1

i = 1
while (i < 13) :
    print(i)
    break

i = 1
while ( i < 13) :
    i += 5
    print(i)
    continue

#continue i == 5
i = 0
z = 2
while( i < 12) :
    i += 1
    if i == 5 :
        continue
    print(str(z) + 'x' + str(i) + '=' + str(z*i) ) #dont show 2*5

#continue i != 5
i = 0
z = 2
while( i < 12) :
    i += 1
    if i != 5 :
        continue
    print(str(z) + 'x' + str(i) + '=' + str(z*i) ) #show 2*5 only