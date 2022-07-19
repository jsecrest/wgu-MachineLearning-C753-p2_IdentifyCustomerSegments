# TODO: NEXT STEP: return a pandas object with 1 entry per var


#%%
import pandas as pd
import re
from typing import Iterator, List, Match, Tuple, Dict, Any
import IPython

# %%

DataFrame = type(pd.DataFrame())

ATTRIB_NAMES_GROUP_INDEX = 1
DEFINITION1_GROUP_INDEX = 2
VALUES_GROUP_INDEX = 3
DESCRIPTION2_GROUP_INDEX = 4


def get_desc_iter() -> Iterator[Match[str]]:
    filename = "data/Data_Dictionary.md"
    with open(filename, "r", encoding="UTF-8") as dd_file:
        doc = dd_file.read()

    desc_str = (
        r"((?:\#{3}[^\n]*\n)+)((?:(?:.*)\n)(?:(?:[^-\n]*)*\n)?)"
        + r"((?:-[ -]+(?:[^\n]*)\n(?: {5}.*\n)?)*)?"
        + r"(?:\n(Dimension translations:\n(?:- .*\n)*))?"
    )
    desc_pat = re.compile(desc_str)
    desc_iter = desc_pat.finditer(doc)
    return desc_iter


# %%
def is_empty_group(g):
    empty_string = r"^\s*$"
    if (g is None) or re.match(pattern=empty_string, string=g) is not None:
        return True


def get_attrib_names(desc_match: Match) -> List[str] | None:
    g = desc_match.group(ATTRIB_NAMES_GROUP_INDEX)
    if is_empty_group(g):
        return None
    attrib_names_str = r"(?:\d\.\d\. )?(\w+)"
    attrib_names = re.findall(pattern=attrib_names_str, string=g)
    return attrib_names


def get_definition(desc_match: Match) -> List[str] | None:
    g = desc_match.group(DEFINITION1_GROUP_INDEX)
    if is_empty_group(g):
        return None
    def_lines_str = r"([^\n]*)\n"
    def_lines = re.findall(pattern=def_lines_str, string=g)
    definition = " ".join(def_lines)
    return [definition]


def get_allowed_values(desc_match: Match) -> DataFrame | None:
    match_group: str = desc_match.group(VALUES_GROUP_INDEX)
    if is_empty_group(match_group):
        return None
    # get the VALUE and the VALUE_DESCRIPTION
    # from example line "-  2: very likely"
    # value is 2, value_description is "very likely"
    symbols_and_defs_str = r"- {1,2}(-?\d+): (.*)\n((?: {5}.*\n)*)"
    symbols_and_defs: List[Tuple(str, str)] | Tuple(str, str, str) = re.findall(
        symbols_and_defs_str, match_group
    )
    if symbols_and_defs is None:
        # deal with "- missing data encoded as 0"
        symbols_and_defs_str = "- (.*)\n"
        symbols_and_defs = re.findall(symbols_and_defs_str, match_group)
        if symbols_and_defs:
            symbols_and_defs = [("0", "missing")]
    if symbols_and_defs is None:
        raise ValueError(
            "No definition found in match.group({VALUES_GROUP_INDEX}): {g}"
        )

    # In a Tuple T in the list,
    #   T[0] is a symbol like "0" or "W" or "-1"
    #   T[1] is the symbol_definition associated with the symbol
    #   T[2] (if it exists) is any number overflow lines from the definition
    #       - Each overflow line starts with 5 spaces and ends with \n

    # process each tuple
    # separate
    symbols = []
    definitions = []
    for t in symbols_and_defs:
        #   When T[2] exists, get its definition values and merge them with T[1]
        definition: str = None
        if len(t) == 3:
            extra_lines: List[str] = re.findall(pattern=" {5}([^\n]+)", string=t[2])
            extra_lines.insert(0, t[1])
            definition = " ".join(extra_lines)
        else:
            if len(t) != 2:
                raise ValueError(f"Expected tuple of len 2 or 3. Got len: {len(t)}")
            definition.append(t[1])
        if definition is None:
            raise ValueError("var 'definition' not set")
        symbols.append(t[0])
        definitions.append(definition)
        # print(symbols, definitions)

    return [
        pd.Series(definitions, index=symbols, dtype="object")
        # [symbols, definitions],
    ]


def get_dim_translate(desc_match: Match) -> List[str] | None:
    g = desc_match.group(DESCRIPTION2_GROUP_INDEX)
    if is_empty_group(g):
        return None
    def_lines_str = r"- (\w*.+)\n?"
    dimensional_translations = re.findall(pattern=def_lines_str, string=g)
    return dimensional_translations


def get_section_df(desc_match: Match[str]) -> DataFrame | None:
    if re.match("### Table of Contents", desc_match.group(1)) is None:
        info_dict = {
            "attrib_names": get_attrib_names(desc_match),
            "definition": get_definition(desc_match),
            "allowed_values": get_allowed_values(desc_match),
            "dim_translation": get_dim_translate(desc_match),
        }
        col_count = len(info_dict["attrib_names"])
        if col_count > 1:
            # index 0 is already set, just need to fill remaining
            for i in range(1, col_count):
                if i >= col_count:
                    raise ValueError("i is too large. i : {i}, col_count : {col_count}")
                info_dict["definition"].append(info_dict["definition"][0])
                info_dict["allowed_values"].append(info_dict["allowed_values"][0])
        # if the dict didn't contain any columns return none
        out_df: pd.DataFrame() = None
        if col_count > 0:
            out_df = pd.DataFrame().from_dict(info_dict)
        return out_df


# %%
def next_match(desc_iter, verbose=True):
    match = next(desc_iter)
    section_df = get_section_df(match)
    if verbose == True and section_df is not None:
        # display(section_df)
        # display(section_df.info())
        # display(section_df.definition)
        # display(section_df.head())
        # section_df.head()
        # section_df.allowed_values
        display(section_df.head())
        display(section_df.loc[0, "allowed_values"])

    return section_df


# %%
if __name__ == "__main__":
    from pprint import pprint

    desc_iter = get_desc_iter()
    next(desc_iter)  # skip the empty Table Of Contents match
    # next_match(desc_iter)


# %%
for i in range(469):
    print(i)
    section_df = next_match(desc_iter, verbose=False)
    print(f"previous: {section_df.attrib_names}")


section_df = next_match(desc_iter, verbose=True)

# %% [markdown]
# Check out this MD
# %%


# %%
