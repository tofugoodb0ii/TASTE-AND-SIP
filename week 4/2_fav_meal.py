#เขียนโปรแกรมรับชื่ออาหารไปเรื่อย ๆ จนกว่าจะพิมพ์คำว่า exit หลังจากพิมพ์คำว่า exit ให้แสดงผล 

favmeallist = []
i = 0
x = 0
print('\npls input your fav meal or type exit to exit the program')
while ( True ) :
    favmeal = (input(f'\ninput your fav meal {i+1}. '))
    favmeallist.append(favmeal)
    i = i+1
    if favmeal == 'exit' :
        break
favmeallist.pop() #pop for delete exit in last input
print('\nthis is your fav meal')
for y in favmeallist :
    print(f'{x+1}.' , y)
    x += 1