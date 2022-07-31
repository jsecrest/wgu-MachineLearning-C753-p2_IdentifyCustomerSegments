
def clean_data(cust_df):
    """
    Perform feature trimming, re-encoding, and engineering for demographics
    data
    
    INPUT: Demographics DataFrame
    OUTPUT: Trimmed and cleaned demographics DataFrame
    """
    codex = cdd.DataCodex(
        data_dict_file="data/Data_Dictionary.md",
        feat_summary_file="data/AZDIAS_Feature_Summary.csv",
    )


    ############## CLEAN NAN

    # years
    year_df = cust_df.loc[:, ["GEBURTSJAHR", "MIN_GEBAEUDEJAHR"]]
    year_df = year_df.applymap(flag_year)
    # numerical
    number_s = cust_df.loc[:, "ANZ_HAUSHALTE_AKTIV"]
    number_s = number_s.map(check_number)


    # for anything else:
    # uses: apply_missing_to_nan(feature_name_list:List[str], inspect:int=None)

    quality_df = cust_df.apply(value_validity_sort).T
    has_nan_df = quality_df.loc[quality_df["nan_codes"] > 0]
    feature_names = has_nan_df.index.to_list()
    cust_df.loc[:, feature_names] = apply_missing_to_nan(feature_names, inspect=10)

    ############ NAN DONE

    ################ REMOVE COLUMNS WITH MISSING DATA

    # It seems to me like we can't just remove ANY columns from the customers data
    # Doesn't it have to be the same ones? Here's what I removed in the larger set:

    drop_features = [
        "TITEL_KZ",
        "AGER_TYP",
        "KK_KUNDENTYP",
        "KBA05_BAUMAX",
        "GEBURTSJAHR",
        "ALTER_HH",
    ]
    cust_df = cust_df.drop(drop_features, axis=1)

    ############ COLUMNS DONE

    ############# REMOVE ROWS

    # How much data is missing in each row of the dataset?
    rows_by_missing_s = cust_df.T.isna().sum()
    threshold = 8 #threshold is INCLUDED in the main data
    cust_df_main = cust_df.loc[rows_by_missing_s <= threshold]
    # cust_df_missing_data = cust_df.loc[rows_by_missing_s > threshold] # save some space unless we need this...
    del cust_df #this was pretty big! Now that we've got it separated, lets delete it.
    del rows_by_missing_s
    ############ ROWS DONE

    # change data type for ordinal/numerical

    type_s = codex.all_df.loc[codex.all_df.index.isin(cust_df_main.columns)].type
    all_numeric_names = codex.all_df.loc[(type_s == "ordinal")|(type_s == "numeric")].index
    cust_df_main.loc[:,all_numeric_names] = cust_df_main.loc[:,all_numeric_names].apply(pd.to_numeric, errors='raise', downcast=None)


    # drop additional mixed features

    type_s = codex.all_df.loc[codex.all_df.index.isin(cust_df_main.columns)].type
    features_to_drop = codex.all_df.loc[type_s == "mixed"].index.drop(["PRAEGENDE_JUGENDJAHRE","CAMEO_INTL_2015"])
    print(features_to_drop)

    features_to_keep = cust_df_main.columns.drop(features_to_drop)
    print(f"keeping {len(features_to_keep)} features of {len(cust_df_main.columns)}")

    cust_df_main.drop(columns = features_to_drop, inplace=True)
    print(len(cust_df_main.columns))


    # ##### engineering 1

    # 1. My awesome little function was able to display an easy piece of text to copy/paste

    pj_text = """1	40s - war years (Mainstream, E+W)
    2	40s - reconstruction years (Avantgarde, E+W)
    3	50s - economic miracle (Mainstream, E+W)
    4	50s - milk bar / Individualisation (Avantgarde, E+W)
    5	60s - economic miracle (Mainstream, E+W)
    6	60s - generation 68 / student protestors (Avantgarde, W)
    7	60s - opponents to the building of the Wall (Avantgarde, E)
    8	70s - family orientation (Mainstream, E+W)
    9	70s - peace movement (Avantgarde, E+W)
    10	80s - Generation Golf (Mainstream, W)
    11	80s - ecological awareness (Avantgarde, W)
    12	80s - FDJ / communist party youth organisation (Mainstream, E)
    13	80s - Swords into ploughshares (Avantgarde, E)
    14	90s - digital media kids (Mainstream, E+W)
    15	90s - ecological awareness (Avantgarde, E+W)"""

    # 2. Regex can easily break this up... I could also use split functions, but I think
    # regex will be more straightforward in this case

    pj_pattern =re.compile(r"(\d+)\s+(\d\d).*\((\w*)")

    # 3. I'll convert the regex matches into a dataframe and then selectively peel the
    # columns to build a mapping dictionary per feature
    pj_df = pd.DataFrame(pj_pattern.findall(pj_text), columns=["code", "YR", "M"])
    pj_df.set_index("code",inplace=True)

    #Don't forget to convert words to numbers in the categorical feature values!
    pj_df.loc[:,"M"] = pj_df.loc[:,"M"].map({"Avantgarde": 0, "Mainstream": 1})

    #new values to dictionaries
    pj_code_to_yr_dict = pj_df.loc[:,["YR"]].to_dict()["YR"]
    pj_code_to_m_dict = pj_df.loc[:,["M"]].to_dict()["M"]

    # Stop and check how our mapping dicts look...
    print(pj_code_to_yr_dict)
    print(pj_code_to_m_dict)

    pj_s = cust_df_main.loc[:,"PRAEGENDE_JUGENDJAHRE"]
    pj_s.head()

    # 4. With a mapping feature, all I have to do is map the series! I'll map it twice and
    # save the results to different series.

    # I often try to end with "_s" or "_df" to indicate that the var is a series or a dataframe...
    # pj_m_s just seemed a bit too cryptic.
    pj_m_series = pj_s.map(pj_code_to_m_dict)
    pj_m_series.name = "PRAEGENDE_JUGENDJAHRE_M"
    pj_yr_series = pj_s.map(pj_code_to_yr_dict)
    pj_yr_series.name = "PRAEGENDE_JUGENDJAHRE_YR"

    #expected transformation, given head() of PRAEGENDE_JUGENDJAHRE
    """
    Code reference:
    3	50s - economic miracle (Mainstream, E+W)
    8	70s - family orientation (Mainstream, E+W)
    14	90s - digital media kids (Mainstream, E+W)
    15	90s - ecological awareness (Avantgarde, E+W)

    Avantgarde = 0
    Mainstream = 1

    Transformed feature:
    1    14 -> 90, 0
    2    15 -> 90, 1
    3     8 -> 70, 0
    4     8 -> 70, 0
    5     3 -> 50, 0
    """

    new_pj = pd.concat([pj_yr_series, pj_m_series], axis=1)
    5. Finally, we drop the old feature from the dataframe and concat the two new features.

    Test first. Doing this all in a one liner
    test = pd.concat([cust_df_main, new_pj], axis=1).drop(columns="PRAEGENDE_JUGENDJAHRE")
    # check output - should show that test (copy of full database) only contains two cols
    # containing old col name
    display(test.loc[:,(test.columns.str.contains("PRAEGENDE_JUGENDJAHRE"))].head())
    #success! persist changes and delete all these big extra DFs
    cust_df_main = test
    del test
    del new_pj
    del pj_df
    del pj_s
    del pj_m_series
    del pj_yr_series


    # engineering 2

    cameo_df = cust_df_main.loc[:,"CAMEO_INTL_2015"]
    print(cameo_df.head())
    #I'm pretty sure that this is a string, but lets just be sure:
    cameo_r = cameo_df.astype(str).map(lambda x: x[0])
    cameo_r.name = "CAMEO_INTL_2015_REICHTUM"
    cameo_l = cameo_df.astype(str).map(lambda x: x[1])
    cameo_l.name = "CAMEO_INTL_2015_LEBENSSTATUS"

    # cameo_new = pd.concat([cameo_r, cameo_l], axis=1)
    # display(cameo_new)
    # Test first. Doing this all in a one liner
    test = pd.concat([cust_df_main, cameo_new], axis=1).drop(columns="CAMEO_INTL_2015")
    # check output - should show that test (copy of full database) only contains two cols
    # containing old col name
    display(test.loc[:,(test.columns.str.contains("CAMEO_INTL_2015"))].head())
    cust_df_main = test
    del test
    del cameo_new
    del cameo_df
    del cameo_l
    del cameo_r


    # imputer

    # imputer_frq = SimpleImputer(strategy="most_frequent")
    test = imputer_frq.fit_transform(cust_df_main)
    test = pd.DataFrame(test)
    test.columns = cust_df_main.columns
    graph_missing(test)
    cust_df_main = test

    del test


    # onehot

    type_s = codex.all_df.type

    categorical_names = type_s.loc[type_s == "categorical"].index
    #we've dropped some features that still exist in the codex. Lets get a cleaner list of categorical names.
    categorical_names = cust_df_main.columns[cust_df_main.columns.isin(categorical_names)].to_list()
    #We've also added a columns that don't appear in the codex. Let's get them added.
    categorical_names.extend([
        'PRAEGENDE_JUGENDJAHRE_YR',
        'PRAEGENDE_JUGENDJAHRE_M',
        'CAMEO_INTL_2015_REICHTUM',
        'CAMEO_INTL_2015_LEBENSSTATUS'])

    # cust_df_main.loc[:,categorical_names]
    not_categorical_names = cust_df_main.columns[(~cust_df_main.columns.isin(categorical_names))]

    print(
        len(categorical_names), "categorical\n",
        len(not_categorical_names), "not categorical\n",
        len(cust_df_main.columns), "expected total\n",
    )

    # I've looked at the defaults and they all seem fine for my purposes.
    # good example of easy use https://stackoverflow.com/questions/71555321/sklearn-preprocessing-onehotencoder-and-the-way-to-read-it
    ohe = OneHotEncoder()
    # one_hot_data = ohe.fit_transform(cust_df_main.loc[:,categorical_names])
    one_hot_data = ohe.transform(cust_df_main.loc[:,categorical_names])
    transformed_categorical = pd.DataFrame(one_hot_data.toarray(), columns=ohe.get_feature_names_out())
    cust_df_main = cust_df_main.drop(columns=categorical_names)
    cust_df_main = pd.concat([cust_df_main, transformed_categorical], axis=1)
    del transformed_categorical


    
    # Return the cleaned dataframe.
    return cust_df_main
