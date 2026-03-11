dictionary = []

def add_vocab() :
    while True :
        vocab = (input('\nplease input vocab or X to Exit : '))
        if  vocab == 'X' :
            break
        else :
            type = (input('please input type of word (n. , v. , adj. , adv. , ect.) : '))
            meaning = (input('please input meaning : '))
            dictionary.append([vocab,type,meaning])
            print('{0:=<74}\n{1:^74}\n{2:=<74}'.format('','-+ The word has been saved +-',''))

def show_vocab() :
    no = 1
    count_w = len(dictionary)
    if count_w == 0 :
        print('\n{0:=<74}'.format(''))
        print('{0:^74}'.format('Dictionary is empty'))
        print('\n{0:=<74}'.format(''))
    else :
        print('\n{0:=<74}\n{1:^74}\n{2:=<74}'.format('',f'-+ Dictionary have {count_w} words +-',''))
        print('{0:<5}{1:<10}{2:^40}{3:<20}'.format('No.','vocab', 'type', 'meaning',))
        print('{0:=<74}'.format(''))
        for x in dictionary :
            print('{0:<5}{1:<5}{2:^50}{3:<15}'.format(no,x[0],x[1],x[2]))
            no += 1

def remove_vocab() :
    while True :
        show_vocab()
        remove_word = input('\ninput vocab to remove (or X to exit) : ')
        if remove_word == 'X' :
            break
        confermation = input(f'\ndo you want to remove {remove_word} (y/n) : ')
        if confermation == 'y' :
            for y in dictionary :
               if y[0] == remove_word :
                   dictionary.remove(y)
                   print(f'\n{remove_word}  has been removed')
        elif confermation == 'n' :
            continue
        else :
            print('error , pls try again')

while True :
    print('\n{0:=<74}'.format(''))
    print('{0:^74}'.format(' -+ Dictionary Program +- '))
    print('{0:=<74}'.format(''))
    print('{0:^74}'.format('MAIN MENU'))
    print('[1] Add Vocab','\n[2] Show Vocab','\n[3] Remove Vocab','\n[4] Exit')
    print('{0:=<74}'.format(''))
    option = input('\nselect an option : ')
    if option == '1':
        add_vocab()
    elif option == '2':
        show_vocab()
    elif option == '3':
        remove_vocab()
    elif option == '4':
        exit = input('do you want to exit (y/n) : ')
        if exit == 'y' :
            break
        elif exit == 'n' :
            continue
        else :
            print('error , pls try again')
    else :
        print('error, please try again')
