#set

thisset = {"Com" , "ED" , "KKU"}
#print(thisset) # run ในแต่ละครั้งจะไม่มีการเรียงลำดับตามตำแหน่งของข้อมูล

#การเข้าถึงข้อมูล
thisset = {"Com" , "ED" , "KKU"}
#for x in thisset :
#print(x) # ไม่สามารถเข้าถึงข้อมูลได้

#การเพิ่มข้อมูลใน set
thisset = {"Com" , "ED" , "KKU"}
#thisset.add("JPN")
#print(thisset) 
#thisset.update(["i" , "am" ,  "atomic"])
#print(thisset)

#การลบข้อมูลใน set
thisset = {"Com" , "ED" , "KKU"}
#thisset.remove("Com")
#print(thisset)

thisset = {"Com" , "ED" , "KKU"}
#thisset.discard("Com")
#print(thisset)

thisset = {"Com" , "ED" , "KKU"}
del thisset # เป็นการลบข้อมูลทั้งหมด
print(thisset)