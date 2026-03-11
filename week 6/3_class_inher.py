class car :
    def __init__(self,name,color) :
        self.name = name
        self.color = color

    def showcar(self) :
        print('information : name = ',self.name,',color = ',self.color)
    
class newcar(car) : #class inheritance สืบทอดคุณสมบัติจาก parent class ให้ child class
    pass
x = newcar('lambokini','yellow')
x.showcar()

#add __init__ to child class
class newcar(car) :
    def __init__(self, name, color) :
        car.__init__(self,name, color)

#super function
class car :
    def __init__(self,name,color) :
        self.name = name
        self.color = color

    def showcar(self) :
        print(self.name,self.color)

class newcar(car) :
    def __init__(self, name, color,gear) : #add new property
        super().__init__(name, color)
        self.gear = gear
x = newcar('lambikini','yellow','auto')
print(x.gear)

#add medthod to child class
class newcar(car) :
    def __init__(self, name, color,gear) : #add new property
        super().__init__(name, color)
        self.gear = gear
        
    def showcar2(self) :
        print(self.name,self.color,self.gear)
x = newcar('lambikini','yellow','auto')
x.showcar2()