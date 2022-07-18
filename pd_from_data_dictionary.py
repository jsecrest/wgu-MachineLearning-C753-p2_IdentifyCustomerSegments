# TODO: NEXT STEP: return a pandas object with 1 entry per var


#%%
import re
from typing import Iterator, List, Match, Union, Tuple

# %%

COL_NAMES_GROUP_INDEX = 1
DEFINITION1_GROUP_INDEX = 2
VALUES_GROUP_INDEX = 3
DESCRIPTION2_GROUP_INDEX = 4


def get_desc_iter() -> Iterator[Match[str]]:
    filename = "data/Data_Dictionary.md"
    with open(filename, "r") as dd_file:
        doc = dd_file.read()

    desc_str = r"((?:\#{3}[^\n]*\n)+)((?:(?:.*)\n)(?:(?:[^-\n]*)*\n)?)((?:-[ -]+(?:[^\n]*)\n(?: {5}.*\n)?)*)?(?:\n(Dimension translations:\n(?:- .*\n)*))?"
    desc_pat = re.compile(desc_str)
    desc_iter = desc_pat.finditer(doc)
    return desc_iter


# %%
def is_empty_group(g):
    empty_string = r"^\s*$"
    if (g is None) or re.match(pattern=empty_string, string=g) is not None:
        return True


def get_col_names(desc_match: Match) -> Union[List[str], None]:
    g = desc_match.group(COL_NAMES_GROUP_INDEX)
    if is_empty_group(g):
        return None
    col_names_str = r"(?:\d\.\d\. )?(\w+)"
    col_names = re.findall(pattern=col_names_str, string=g)
    return col_names


def get_definition1(desc_match: Match) -> Union[str, None]:
    g = desc_match.group(DEFINITION1_GROUP_INDEX)
    if is_empty_group(g):
        return None
    def_lines_str = r"([^\n]*)\n"
    def_lines = re.findall(pattern=def_lines_str, string=g)
    definition1 = " ".join(def_lines)
    return definition1


def get_values(desc_match: Match) -> Union[Tuple[str, str], None]:
    g = desc_match.group(VALUES_GROUP_INDEX)
    if is_empty_group(g):
        return None
    # get the VALUE and the VALUE_DESCRIPTION
    # from example line "-  2: very likely"
    # value is 2, value_description is "very likely"
    values_line_a_str = r"- {1,2}(-?\d+): (.*)\n"
    value_and_vd = re.findall(values_line_a_str, g)
    if value_and_vd is None:
        # deals with "- missing data encoded as 0"
        values_line_a_str = "- (.*)\n"
        value_and_vd = re.findall(values_line_a_str, g)
        if value_and_vd:
            value_and_vd = ["0", "missing"]
    if value_and_vd is None:
        raise ValueError(
            "No definition found in match.group({VALUES_GROUP_INDEX}): {g}"
        )
    # sometimes the value description is multiple lines
    vd_extras_str = r" {5}(.*)\n"
    vd_extras = re.findall(vd_extras_str, g)
    # string it all together and return
    value = value_and_vd[0]
    value_description = value_and_vd[1]
    if vd_extras:
        value_description += " " + " ".join(vd_extras)
    return value, value_description


def get_dim_translate(desc_match: Match) -> Union[List[str], None]:
    g = desc_match.group(DESCRIPTION2_GROUP_INDEX)
    if is_empty_group(g):
        return None
    def_lines_str = r"- (\w*.+)\n?"
    dimensional_translations = re.findall(pattern=def_lines_str, string=g)
    return dimensional_translations


def process_desc_match(desc_match: Match[str]):
    if re.match("### Table of Contents", desc_match.group(1)) is None:
        info_dict = {
            "col_names": get_col_names(desc_match),
            "definition1": get_definition1(desc_match),
            "allowed_values": get_values(desc_match),
            "definition2": get_dim_translate(desc_match),
        }
        return info_dict


# %%
from pprint import pprint


def test():
    desc_iter = get_desc_iter()
    i = 0
    for match in desc_iter:
        g2 = match.group(2)
        print(f"MATCH #: {i}")
        pprint(match.groups())
        pprint(process_desc_match(match))
        print("\n-----------\n")
        i += 1
        if i >= 5:
            break


test()


# %% [markdown]
# Check out this MD
# %%
