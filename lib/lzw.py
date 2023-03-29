def compress(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    dictionary = {bytes([i]): i for i in range(256)}
    result = []
    w = bytes()
    for c in data:
        wc = w + bytes([c])
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            dictionary[wc] = len(dictionary)
            w = bytes([c])
    if w:
        result.append(dictionary[w])
    return result


def decompress(data):
    dictionary = {i: bytes([i]) for i in range(256)}
    if isinstance(data, str):
        data = list(map(ord, data))
    w = bytes([data.pop(0)])
    result = [w.decode("utf-8")]
    for k in data:
        if k in dictionary:
            entry = dictionary[k]
        elif k == len(dictionary):
            entry = w + bytes([w[0]])
        else:
            raise ValueError("Bad compressed k: %s" % k)
        result.append(entry.decode("utf-8"))
        dictionary[len(dictionary)] = w + bytes([entry[0]])
        w = entry
    return "".join(result)


if __name__ == "__main__":
    data = "The quick brown fox jumped over the lazy dog." * 10
    compressed = compress(data)
    reconstructed = decompress(compressed)
    assert data == reconstructed

    print(f"Raw: {len(data)}")
    print(f"Compressed: {len(compressed)}")
