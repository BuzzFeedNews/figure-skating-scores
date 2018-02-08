class EmptyResultsException(Exception):
    pass

def dictify(df):
    if df is None:
        return None
    else:
        return df.to_dict("records")
