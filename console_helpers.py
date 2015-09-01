"""
Reqiures colorama package.
"""
try:
    from colorama import init, Fore

    init(autoreset=True)

    def print_red(*o):
        print(Fore.RED + str(list(o)[0]), *list(o)[1:])

    def print_green(*o):
        print(Fore.GREEN + str(list(o)[0]), *list(o)[1:])

except ImportError:
    print_red = print_green = lambda *o: print(o)
