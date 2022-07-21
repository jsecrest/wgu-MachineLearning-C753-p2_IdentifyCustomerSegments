# TODO: NEXT STEP: return a pandas object with 1 entry per var


#%%
import re
from typing import Iterator, List, Match, Tuple, Dict
import pandas as pd
import IPython

# %%

DataFrame = type(pd.DataFrame())
Series = type(pd.Series())

FEATURE_NAMES_GROUP_INDEX = 1
DEFINITION1_GROUP_INDEX = 2
VALUES_GROUP_INDEX = 3
DESCRIPTION2_GROUP_INDEX = 4


def get_desc_iter(filename) -> Iterator[Match[str]]:
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
def is_empty_group(group):
    empty_string = r"^\s*$"
    if (group is None) or re.match(pattern=empty_string, string=group) is not None:
        return True


def get_feature_names(desc_match: Match) -> List[str] | None:
    feature_group = desc_match.group(FEATURE_NAMES_GROUP_INDEX)
    if is_empty_group(feature_group):
        return None
    feature_names_str = r"(?:\d+\.\d+\. )?(\w+)"
    section_no_str = r"(\d+\.\d+\.)"
    feature_names = re.findall(pattern=feature_names_str, string=feature_group)
    section_no = [re.search(pattern=section_no_str, string=feature_group).group(1)]
    for _ in range(1, len(feature_names)):
        section_no.append(section_no[0])
    if len(feature_names) != len(section_no):
        raise ValueError("section_no is not the same length as feature_names")
    return feature_names, section_no


def get_definition(desc_match: Match) -> List[str] | None:
    def_group = desc_match.group(DEFINITION1_GROUP_INDEX)
    if is_empty_group(def_group):
        return None
    def_lines_str = r"([^\n]*)\n"
    def_lines = re.findall(pattern=def_lines_str, string=def_group)
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
    for feature_tuple in symbols_and_defs:
        #   When T[2] exists, get its definition values and merge them with T[1]
        definition: str = None
        if len(feature_tuple) == 3:
            extra_lines: List[str] = re.findall(
                pattern=" {5}([^\n]+)", string=feature_tuple[2]
            )
            extra_lines.insert(0, feature_tuple[1])
            definition = " ".join(extra_lines)
        else:
            if len(feature_tuple) != 2:
                raise ValueError(
                    f"Expected tuple of len 2 or 3. Got len: {len(feature_tuple)}"
                )
            definition.append(feature_tuple[1])
        if definition is None:
            raise ValueError("var 'definition' not set")
        symbols.append(feature_tuple[0])
        definitions.append(definition)
        # print(symbols, definitions)

    return [
        pd.Series(definitions, index=symbols, dtype="object")
        # [symbols, definitions],
    ]


def get_dim_translate(desc_match: Match) -> List[str] | None:
    desc_group = desc_match.group(DESCRIPTION2_GROUP_INDEX)
    if is_empty_group(desc_group):
        return None
    def_lines_str = r"- (\w*.+)\n?"
    dimensional_translations = re.findall(pattern=def_lines_str, string=desc_group)
    return dimensional_translations


def get_section_df(desc_match: Match[str]) -> DataFrame | None:
    # only try to process this match if it isn't the table of contents
    if re.match("### Table of Contents", desc_match.group(1)) is None:
        info_dict = {
            "feature_name": get_feature_names(desc_match)[0],
            "section_no": get_feature_names(desc_match)[1],
            "definition": get_definition(desc_match),
            "codes": get_allowed_values(desc_match),
            "dim_translation": get_dim_translate(desc_match),
        }
        col_count = len(info_dict["feature_name"])
        if col_count > 1:
            # index 0 is already set, just need to fill remaining
            for i in range(1, col_count):
                if i >= col_count:
                    raise ValueError("i is too large. i : {i}, col_count : {col_count}")
                info_dict["definition"].append(info_dict["definition"][0])
                info_dict["codes"].append(info_dict["codes"][0])
        # if the dict didn't contain any columns return none
        out_df: pd.DataFrame() = None
        if col_count > 0:
            out_df = pd.DataFrame(data=info_dict)
            # out_df = out_df.set_index(["feature_name"])
        return out_df


# %%
def get_value_meaning(df, feature_name, value):
    code = str(value)
    if feature_name not in df.loc[:, "feature_name"]:
        raise ValueError(
            f"{feature_name} not found in feature_name: {df.loc[:, 'feature_name']}."
        )
    if code in df.allowed_values[0].index:
        return df.allowed_values[0].loc[code]
    else:
        return None


def _next_match(desc_iter, verbose=False):
    """
    for testing
    gets the next non-null dataframe
    >>> section_df = _next_match(desc_iter, verbose=True)
    """
    section_df = None
    while section_df is None:
        match = next(desc_iter)
        section_df = get_section_df(match)
        if verbose:
            if section_df is None:
                print("Match does not contain feature data.")
    if verbose:
        # display(section_df)
        # display(section_df.info())
        # display(section_df.definition)
        print(section_df.head())
        # print(section_df.loc[:, "codes"])
    return section_df


def get_data_dict_as_df(filename) -> DataFrame:
    data_df: DataFrame = None
    desc_iter = get_desc_iter(filename)
    for match in desc_iter:
        section_df = get_section_df(match)
        if section_df is not None:
            if data_df is None:
                data_df = section_df
            else:
                data_df = pd.concat([data_df, section_df])
    if data_df is None:
        print(
            "Not able to create DataFrame from data dictionary file (No appropriate regex matches)"
        )
    return data_df


def get_feature_summary_as_df(filepath) -> DataFrame:
    fsum_df = pd.read_csv(filepath, sep=";")
    fsum_df = fsum_df.rename(columns={"attribute": "feature_name"})
    return fsum_df


# %%
class DataCodex:
    """
    Parses Data_Dictionary.md and provides helper functions for getting entries.
    """

    def __init__(self, data_dict_file, feat_summary_file):
        self.data_df: DataFrame = get_data_dict_as_df(data_dict_file)
        self.fsum_df: DataFrame = get_feature_summary_as_df(feat_summary_file)

        display(self.fsum_df.head(2))
        display(self.data_df.head(2))

        self.all_df: DataFrame = self.data_df.merge(
            self.fsum_df, how="left", on="feature_name"
        )

        display(self.all_df.head(2))
        self.all_df.set_index(["feature_name"], inplace=True)
        print("TEMP CHECK")  # TODO YOU ARE HERE
        f_as_basic_s = self.all_df.xs("feature_name")
        display(f_as_basic_s)

    def get_feature_as_s(self, feature_name) -> Series:
        f_as_basic_s = self.data_df.xs(feature_name)
        allowed_values = f_as_basic_s.xs("codes").index.to_list()
        added_feature_name = pd.Series([feature_name], index=["feature_name"])
        added_value_summary = pd.Series([allowed_values], index=["allowed_values"])
        # todo: add feature summary info for missing value codes
        return pd.concat([added_feature_name, f_as_basic_s, added_value_summary])

    def get_feature_as_df(self, feature_name) -> DataFrame:
        return self.get_feature_as_s(feature_name).to_frame()

    def get_feature_as_dict(self, feature_name) -> Dict:
        return self.get_feature_as_s(feature_name).to_dict()

    def nice_print_feature(self, feature_name) -> None:
        feature_dict = self.get_feature_as_dict(feature_name)
        for key, value in feature_dict.items():
            if key != "codes":
                print(f"{key:>15}: {value}")
        print("CODES:")
        print(feature_dict["codes"])

    def nice_display_feature(self, feature_name) -> None:
        s = self.get_feature_as_s(feature_name)
        partial_df = s.drop(index=["codes"]).to_frame()
        partial_df.index.name = "attribute"
        partial_df.columns = ["value"]
        display(partial_df)

        code_df = s["codes"].to_frame()
        code_df.index.name = "code"
        code_df.columns = ["description"]
        display(code_df)


# %%
if __name__ == "__main__":
    from pprint import pprint

    data_codex = DataCodex(
        data_dict_file="data/Data_Dictionary.md",
        feat_summary_file="data/AZDIAS_Feature_Summary.csv",
    )
    feature_name = "FINANZ_MINIMALIST"
    # %%
    data_codex.nice_print_feature(feature_name)
    # %%
    data_codex.nice_display_feature(feature_name)

# %%


# %% [markdown]
# Check out this MD
# %%


# %%
