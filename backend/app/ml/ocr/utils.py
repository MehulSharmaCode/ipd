# Verhoeff algorithm for Aadhaar checksum validation
# Source: https://en.wikipedia.org/wiki/Verhoeff_algorithm

# Multiplication table
d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Permutation table
p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

# Inverse table
inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_aadhar(aadhar_num: str) -> bool:
    """
    Validate Aadhaar number using Verhoeff algorithm.
    The string should be exactly 12 digits.
    """
    if not aadhar_num or len(aadhar_num) != 12 or not aadhar_num.isdigit():
        return False
    
    # Aadhaar must not start with 0 or 1
    if aadhar_num[0] in ['0', '1']:
        return False
        
    c = 0
    # Reverse number and process with tables
    for i, digit in enumerate(reversed(aadhar_num)):
        c = d[c][p[i % 8][int(digit)]]
    
    return c == 0
