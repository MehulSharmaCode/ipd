def encode_boolean(value):
    if value in ["yes", "true", 1]:
        return 1
    return 0