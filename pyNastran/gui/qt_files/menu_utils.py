from six import string_types


def eval_float_from_string(value_str):
    """
    Allows for basic calculator functionality in legend menus.

    ..note :: I don't really care about the speed since it's for a GUI.
    """
    value_str = str(value_str)
    if not isinstance(value_str, string_types):
        raise ValueError('%s  must be a string' % value_str)
    if len(value_str)  > 50:
        raise ValueError('%s must be less than 50 characters' % value_str)
    allowed_letters = r'0123456789.()+-*/'

    for letter in value_str:
        if letter not in allowed_letters:
            raise ValueError('%r is an invalid character' % allowed_letters)
    return eval(value_str)
