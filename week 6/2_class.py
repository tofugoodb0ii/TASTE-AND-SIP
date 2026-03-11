class classname :
    name = "I'm class"
x = classname()
print(x.name)

class car :
    def __init__(self,name,color) : #function __init__
        self.name = name
        self.color = color
x = car("civic","blue")
print(x.name) 
print(x.color) 

class car :
    def __init__(self,name,color) :
        self.name = name
        self.color = color

    def showcar(self) :
        print('car information')
        print('name : ',self.name)
        print('color : ',self.color)

x = car('civic','blue')
x.showcar()

class car :
    def __init__(self,name,color) :
        self.name = name
        self.color = color

    def showcar(self) :
        print('car information')
        print('name : ',self.name)
        print('color : ',self.color)

mustang = car('Mustang','red')
mustang.color = 'black' #change  object property
mustang.showcar()

class car :
    def __init__(self,name,color) :
        self.name = name
        self.color = color

    def showcar(self) :
        print('car information')
        print('name : ',self.name)
        print('color : ',self.color)

byd = car('byd','white')
byd.color = 'nevy' #change  object property
byd.showcar()