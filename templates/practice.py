#occurence
n = int(input())
s = input()
freq = {}
for ch in s:
    if ch in freq:
        freq[ch] += 1
    else:
        freq[ch] = 1
counts = []
for value in freq.values():
    counts.append(value)
counts.sort(reverse=True)
removed = 0
for i in range(min(3, len(counts))):
    removed += counts[i]
print(n - removed)


#file version
def latestVersion(input1, input2):
    max_version = -1
    for filename in input1:
        if filename.startswith("File_"):
            version_str = filename[5:]
            if version_str.isdigit():
                version_num = int(version_str)
                if version_num > max_version:
                    max_version = version_num
    return max_version
input1 = int(input())
input2 = []
for i in range(input1):
    input2.append(input())
print(latestVersion(input2, input1))


#sandwich problem
def getSandwichBreads(s: str) -> str:
    result = []
    i = 0
    n = len(s)
    while i < n:
        bread_char = s[i]
        j = s.find(bread_char, i + 1)
        if j != -1:
            result.append(bread_char)
            i = j + 1
        else:
            i += 1
    return "".join(result)
if __name__ == "__main__":
    input_str = input().strip()
    output = getSandwichBreads(input_str)
    print(output)