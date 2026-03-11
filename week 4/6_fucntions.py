#function
#def introduce() :
    #print("hello , i am function")
    #print("i'll do nothing at all")
    #print("call me if you need help")
#introduce()



#arguments
#def introduce(names) : 
#    print("hello , i am " +names)
#introduce("python") # add str(python) in names

#x = str(input("pls input your name : " )) # add input str(x)
#def introduce(x) :
#    print("hello , i am " +x)
#introduce(x)




#keyword argument
#def introduce(province , nation) : 
#    print("hello , i come from " +province+","+nation )
#introduce("khonkaen ", "Thailand")

#province = str(input("pls input ur province ")) 
#nation = str(input("pls input ur nation "))
#def introduce(province , nation) : 
#    print("hello , i come from " +province+","+nation )
#introduce(province , nation) 



def introduce(arg1, arg2="com",arg3="ed",arg4="kku") :
    print("hello,I'm " + arg1 + "," + arg2 + "," + arg3 + "," + arg4)

introduce("Python") # 1 position argument
introduce(arg1 = "Python") # 1 keyword argument
introduce(arg1 = "Python" , arg3 = "Sci" ) # 2 keyword arguments
introduce ("Python", arg4 = "CMU") # position position, 1 keyword argument

#introduce() 
#introduce(arg1 = "Python" , "CMU") # non-kwarg after kwarg
#introduce("Python 2" , arg1 = "python 3" ) # same argument
#introduce(arg99 = "CMU") # unknown kwarg

#Arbitrary argument และ Arbitrary keywork argument
def introduce (name, *hobby, **address) : # * is tuple , ** is dictionary (kwagr)
    print ("Hello, I am "+name+".")
    print ("My address : ") 
    for kw in address :
        print (kw + ":" + address [kw])
    print ("My hobby : ") 
    for arg in hobby :
        print (arg)
introduce ('P', 'Sport', 'Music', 'game' ,province = 'Khon Kaen', nation = 'Thailand')