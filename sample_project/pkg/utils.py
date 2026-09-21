import os
import subprocess

PASSWORD = "hardcoded_secret_123"

def run_command(user_input):
    # Security issue: shell injection
    os.system("echo " + user_input)
    result = subprocess.call(user_input, shell=True)
    return result

def complex_function(a, b, c, d, e, f, g, h):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            if g:
                                if h:
                                    return 1
                                else:
                                    return 2
                            else:
                                return 3
                        else:
                            return 4
                    else:
                        return 5
                else:
                    return 6
            else:
                return 7
        else:
            return 8
    else:
        return 9
