from subprocess import DEVNULL, STDOUT, check_call
from traceback import TracebackException

WINE = ['wine']

def printEx(e):
    print("".join(TracebackException.from_exception(e).format()))

def silent_run(command, **kawrgs):
    command = [str(i) for i in command]
    try:
        return check_call(command, stdout = DEVNULL, stderr = STDOUT, **kawrgs)
    except Exception as ex:
        print(f"Silent_run error:\n", command)
        printEx(ex)



silent_run(WINE + ['./autotune.exe', '-b', 75, base, over, filename])