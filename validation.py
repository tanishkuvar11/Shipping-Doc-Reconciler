def _build_letter_values():
    values={}
    n=10
    
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        while n%11==0:
            n+=1
        values[letter]=n
        n+=1
    return values

LETTER_VALUES = _build_letter_values()


def container_check_digit(container_no: str):
    
    c=container_no.strip().upper().replace(" ", "")

    if len(c)!=11:
        return False, f"Expected 11 characters, got {len(c)}"
    
    if not c[:4].isalpha():
        return False, "First 4 characters must be alphabets"
    
    if not c[4:].isdigit():
        return False, "Last 7 characters must be digits"
    
    body=c[:10]
    stated_check=int(c[10])

    total=0
    for i, char in enumerate(body):
        if char.isalpha():
            value=LETTER_VALUES[char]
        else:
            value=int(char)

        total+=value*(2**i)
        
    computed=total%11
    if computed==10:
        computed=0

    if computed==stated_check:
        return True, "Valid ISO 6346 check digit"
    else:
        return False, f"Check digit mismatch: stated {stated_check}, computed {computed}"


if __name__ == "__main__":

    tests = [
        ("CSQU3054383", True), 
        ("CSQU3054384", False),
        ("MSCU7392105", True),
        ("ABC123", False),
    ]
    for number, expected in tests:
        ok, reason = container_check_digit(number)
        flag = "OK " if ok == expected else "!! "
        print(f"[{flag}] {number:14} valid={ok!s:5} (expected {expected!s:5})  {reason}")