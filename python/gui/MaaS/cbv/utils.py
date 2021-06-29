def extract_log_data(kwargs):
    """
    Extracts standard names messages from kwargs

    :param kwargs: A dictionary of named arguments

    """
    # If a list of error messages wasn't passed, create one
    if 'errors' not in kwargs:
        errors = list()
    else:
        # Otherwise continue to use the passed in list
        errors = kwargs['errors']  # type: list

    # If a list of warning messages wasn't passed create one
    if 'warnings' not in kwargs:
        warnings = list()
    else:
        # Otherwise continue to use the passed in list
        warnings = kwargs['warnings']  # type: list

    # If a list of basic messages wasn't passed, create one
    if 'info' not in kwargs:
        info = list()
    else:
        # Otherwise continue to us the passed in list
        info = kwargs['info']  # type: list
    return errors, warnings, info


    # Define a function that will make words friendlier towards humans. Text like 'hydro_whatsit' will
    # become 'Hydro Whatsit'
def humanize(words: str) -> str:
    """
    Make certain words more human-readable.

    A function that makes words in certain formats friendlier towards humans. Individual words joined by "_" are
    separated and then titlecased.  E.g., text like 'hydro_whatsit' will become 'Hydro Whatsit'.

    Parameters
    ----------
    words : str
        A string of text to potentially make more human-readable.

    Returns
    -------
    str
        A more human-readable version of the string.
    """
    split = words.split("_")
    return " ".join(split).title()
