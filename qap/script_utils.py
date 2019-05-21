
qap_types = ["anatomical_spatial",
             "functional_spatial",
             "functional_temporal"]


def read_txt_file(txt_file):
    """Read in a text file into a list of strings.

    :type txt_file: str
    :param txt_file: Filepath to the text file.
    :rtype: list
    :return: A list of strings, the lines in the text file.

    """

    with open(txt_file, "r") as f:
        strings = f.read().splitlines()
    return strings


def read_yml_file(yml_file):
    """Read in a YAML file into a dictionary.

    :type yml_file: str
    :param yml_file: Filepath to the YAML file.
    :rtype: dict
    :return: Dictionary of the data stored in the YAML
    """

    import os
    import yaml
    with open(os.path.realpath(yml_file), "r") as f:
        config = yaml.load(f)
    return config


def gather_filepath_list(site_folder):
    """Gather all of the NIFTI files under a provided directory.

    :type site_folder: str
    :param site_folder: Path to the base directory containing all of the
                        NIFTI files you wish to gather.
    :rtype: list
    :return: A list of relative filepaths to the NIFTI files found within and
             under the provided site folder.
    """

    import os

    filepath_list = []
    for root, folders, files in os.walk(site_folder):
        for filename in files:
            fullpath = os.path.join(root, filename)
            if ".nii" in fullpath:
                filepath_list.append(fullpath.replace(site_folder + "/", ""))

    return filepath_list


def csv_to_pandas_df(csv_file):
    """Convert the data in a CSV file into a Pandas DataFrame.

    :type csv_file: str
    :param csv_file: The filepath to the CSV file to be loaded.
    :rtype: Pandas DataFrame
    :return: A DataFrame object with the data from the CSV file.
    """

    import pandas as pd
    from qap.qap_utils import raise_smart_exception

    data = []
    try:
        data = pd.read_csv(csv_file, dtype={"Participant": str})
    except Exception as e:
        err = "Could not load the CSV file into a DataFrame using Pandas." \
              "\n\nCSV file: {}\n\nError details: {}\n\n".format(csv_file, e)
        raise_smart_exception(locals(), err)

    return data


def parse_raw_data_list(filepath_list, site_folder, inclusion_list=None):
    """Parse a list of NIFTI filepaths into a participant data dictionary for
    the 'qap_raw_data_sublist_generator.py' script.

    - This is for the 'qap_sublist_generator.py' script.
    - This is designed for data directories formatted as such:
        /site_folder/participant_ID/session_ID/scan_ID/filename.nii.gz
    - Not for BIDS datasets.

    :type filepath_list: list
    :param filepath_list: A list of input file NIFTI filepaths.
    :type site_folder: str
    :param site_folder: The root directory containing the NIFTI filepaths in
                        the list.
    :type inclusion_list: list
    :param inclusion_list: (default: None) A list of participant IDs to
                           include in the sublist dictionary.
    :rtype: dict
    :return: A dictionary containing the NIFTI files indexed by participant
             information.
    """

    import os

    sub_dict = {}
    if not inclusion_list:
        inclusion_list = []
        inclusion = False
    else:
        inclusion = True
    
    for rel_path in filepath_list:
            
        # /path_to_site_folder/subject_id/session_id/scan_id/..
        fullpath = os.path.join(site_folder, rel_path)
        second_half_list = rel_path.split("/")
        filename = second_half_list[-1]

        if ".nii" not in filename:
            continue

        # the previous try catch block was 300ns longer than checking for the empty string first (514 vs 208ns)
        if "" in second_half_list:
            second_half_list.remove("")

        try:
            site_id = second_half_list[-5]
            subject_id = second_half_list[-4]
            session_id = second_half_list[-3]
            scan_id = second_half_list[-2]
        except IndexError:
            err = "\n\n[!] Could not parse the data directory " \
                  "structure for this file - is it in the " \
                  "correct format?\nFile path:\n{0}\n\nIt should "\
                  "be something like this:\n/site_folder/subject"\
                  "_id/session_id/scan_id/file.nii.gz\n\n".format(rel_path)
            # do not raise an exception, just want to warn the user
            print(err)
            continue

        if not inclusion:
            inclusion_list.append(subject_id)

        resource = None

        if ("anat" in scan_id) or ("anat" in filename) or ("mprage" in filename):
            resource = "anatomical_scan"
            
        if ("rest" in scan_id) or ("rest" in filename) or ("func" in scan_id) or ("func" in filename):
            resource = "functional_scan"

        if (resource == "anatomical_scan") and \
                (subject_id in inclusion_list):

            if subject_id not in sub_dict.keys():
                sub_dict[subject_id] = {}
            
            if session_id not in sub_dict[subject_id].keys():
                sub_dict[subject_id][session_id] = {}
            
            if resource not in sub_dict[subject_id][session_id].keys():
                sub_dict[subject_id][session_id][resource] = {}
                sub_dict[subject_id][session_id]["site_name"] = site_id
                                               
            if scan_id not in sub_dict[subject_id][session_id][resource].keys():
                sub_dict[subject_id][session_id][resource][scan_id] = fullpath
                
        if (resource == "functional_scan") and (subject_id in inclusion_list):

            if subject_id not in sub_dict.keys():
                sub_dict[subject_id] = {}
            
            if session_id not in sub_dict[subject_id].keys():
                sub_dict[subject_id][session_id] = {}
            
            if resource not in sub_dict[subject_id][session_id].keys():
                sub_dict[subject_id][session_id][resource] = {}
                sub_dict[subject_id][session_id]["site_name"] = site_id
                            
            if scan_id not in sub_dict[subject_id][session_id][resource].keys():
                sub_dict[subject_id][session_id][resource][scan_id] = fullpath

    if len(sub_dict) == 0:
        err = "\nThe participant list came out empty! Double-check your " \
              "settings.\n"
        raise Exception(err)

    return sub_dict


def populate_custom_data_dict(data_dict, filepath, part_id, session_id,
                              series_id, site_id, resource,
                              default_series_label=None):
    """Update a participant data dictionary with a NIFTI filepath keyed to
    a participant's information, for the 'gather_custom_raw_data.py' script.

    - This is for the 'gather_custom_raw_data.py' script, but is called in
      the 'gather_custom_raw_data' function, one NIFTI file at a time.

    :type data_dict: dict
    :param data_dict: The participant data dictionary.
    :type filepath: str
    :param filepath: The new NIFTI filepath to add to the dictionary.
    :type part_id: str
    :param part_id: The participant ID.
    :type session_id: str
    :param session_id: The session ID.
    :type series_id: str
    :param series_id: The series/scan ID.
    :type site_id: str
    :param site_id: The site name/ID.
    :type resource: str
    :param resource: The name of the type of data/file the NIFTI file is.
    :type default_series_label: str
    :param default_series_label: (default: None) A default to use for series/
                                 scan names/IDs.
    :rtype: dict
    :return: The updated version of the data_dict provided in the inputs.
    """

    new_dict = data_dict

    if not session_id:
        session_id = "session_1"
    if not series_id:
        if default_series_label:
            series_id = default_series_label
        else:
            series_id = "scan_1"

    if part_id not in new_dict.keys():
        new_dict[part_id] = {}
    if session_id not in new_dict[part_id].keys():
        new_dict[part_id][session_id] = {}
    if resource not in new_dict[part_id][session_id].keys():
        new_dict[part_id][session_id][resource] = {}
    if site_id not in new_dict[part_id][session_id].keys():
        new_dict[part_id][session_id]["site_name"] = site_id
    if series_id not in new_dict[part_id][session_id][resource].keys():
        new_dict[part_id][session_id][resource][series_id] = filepath    

    data_dict.update(new_dict)

    return data_dict


def gather_custom_raw_data(filepath_list, base_folder, directory_format, anatomical_keywords=None,
                           functional_keywords=None):
    """Parse a list of NIFTI filepaths into a participant data dictionary 
    when the NIFTI filepaths are based on a custom data directory format, for
    the 'qap_flexible_sublist_generator.py' script.

    - This is for the 'qap_flexible_sublist_generator.py' script.
    - This is to facilitate participant dictionary generation for data
      directory formats that are neither BIDS-format nor conventional
      (/site/participant/session/scan/file).

    :type filepath_list: list
    :param filepath_list: A list of NIFTI filepaths.
    :type base_folder: str
    :param base_folder: The root directory containing all of the NIFTI
                        filepaths in the list.
    :type directory_format: str
    :param directory_format: A string describing the data directory layout in
                             the format '/{site}/{participant}/{session}/..'
                             etc. where the order of the {} items can vary.
    :type anatomical_keywords: str
    :param anatomical_keywords: (default: None) A string of space-delimited
                                keywords that may be in the NIFTI filepath or
                                filename that denotes the file is anatomical.
    :type functional_keywords: str
    :param functional_keywords: (default: None) A string of space-delimited
                                keywords that may be in the NIFTI filepath or
                                filename that denotes the file is functional.
    :rtype: dict
    :return: The participant data dictionary.
    """

    import os

    if "{participant}" not in directory_format:
        pass

    data_dict = {}

    base_folder = os.path.abspath(base_folder)
    format_list = [x for x in directory_format.split("/") if x != ""]

    indices = {}
    operators = ["{site}", "{participant}", "{session}", "{series}"]

    for op in operators:
        if op in format_list:
            indices[op] = format_list.index(op)

    if anatomical_keywords:
        anatomical_keywords = [x for x in anatomical_keywords.split(" ") if x != ""]

    if functional_keywords:
        functional_keywords = [x for x in functional_keywords.split(" ") if x != ""]

    for filepath in filepath_list:

        second_half_list = [x for x in filepath.split(base_folder)[1].split("/") if x != ""]
        filename = second_half_list[-1]

        site_id = None
        part_id = None
        session_id = None
        series_id = None

        if "{site}" in indices.keys():
            site_id = second_half_list[indices["{site}"]]
        if "{participant}" in indices.keys():
            part_id = second_half_list[indices["{participant}"]]
        if "{session}" in indices.keys():
            session_id = second_half_list[indices["{session}"]]
        if "{series}" in indices.keys():
            series_id = second_half_list[indices["{series}"]]

        if anatomical_keywords:
            for word in anatomical_keywords:
                if (word in filename) or (word in session_id):
                    data_dict = populate_custom_data_dict(data_dict,
                                                          filepath, part_id,
                                                          session_id,
                                                          series_id,
                                                          site_id,
                                                          "anatomical_scan",
                                                          "anat_1")

        if functional_keywords:
            for word in functional_keywords:
                if (word in filename) or (word in session_id):
                    data_dict = populate_custom_data_dict(data_dict,
                                                          filepath, part_id,
                                                          session_id,
                                                          series_id,
                                                          site_id,
                                                          "functional_scan",
                                                          "func_1")

    if len(data_dict) == 0:
        err = "\n\n[!] No data files were found given the inputs you " \
              "provided! Double-check your setup.\n\n"
        raise Exception(err)

    return data_dict


def pull_s3_sublist(data_folder, creds_path=None):
    """Create a list of filepaths stored on the Amazon S3 bucket.

    :type data_folder: str
    :param data_folder: The full S3 (s3://) path to the directory holding the
                        data.
    :type creds_path: str
    :param creds_path: The filepath to your Amazon AWS keys.
    :rtype: list
    :return: A list of Amazon S3 filepaths from the bucket and bucket
             directory you provided.
    """

    import os
    from indi_aws import fetch_creds

    if creds_path:
        creds_path = os.path.abspath(creds_path)

    s3_path = data_folder.split("s3://")[1]
    bucket_name = s3_path.split("/")[0]
    bucket_prefix = s3_path.split(bucket_name + "/")[1]

    s3_list = []
    bucket = fetch_creds.return_bucket(creds_path, bucket_name)

    # ensure slash at end of bucket_prefix, so that if the final
    # directory name is a substring in other directory names, these
    # other directories will not be pulled into the file list
    if "/" not in bucket_prefix[-1]:
        bucket_prefix += "/"

    # Build S3-subjects to download
    for bk in bucket.objects.filter(Prefix=bucket_prefix):
        s3_list.append(str(bk.key).replace(bucket_prefix, ""))

    return s3_list


def gather_json_info(output_dir):
    """Extract the dictionaries from the JSON output files and merge them into
    one dictionary.

    :type output_dir: str
    :param output_dir: The path to the main output directory of the QAP run.
    :rtype: dict
    :return: The output data of the QAP run keyed by participant-session-scan.
    """

    import os
    from qap.qap_utils import read_json

    json_dict = {}

    for root, dirs, files in os.walk(os.path.abspath(output_dir)):
        for filename in files:
            if ".json" in filename:
                filepath = os.path.join(root, filename)
                temp_dict = read_json(filepath)
                json_dict.update(temp_dict)

    return json_dict

    
def json_to_csv(json_dict, csv_output_dir=None):
    """Extract the data from the JSON output file and write it to a CSV file.

    :type json_dict: dict
    :param json_dict: Dictionary containing all of the JSON output information
                      from the QAP run.
    :type csv_output_dir: str
    :param csv_output_dir: (default: None) Path to the directory to write the
                           CSV file into.
    :rtype: str
    :return: The CSV file path.
    """

    import os
    import pandas as pd

    output_dict = {}
    csv_file = ""

    for sub_sess_scan in json_dict.keys():
        # flatten the JSON dict
        sub_json_dict = json_dict[sub_sess_scan]
        header_dict = {}

        # TODO: this code doesnt seem to do anything ?? header_dict is overwritten at the next opportunity
        try:
            header_dict = sub_json_dict["anatomical_header_info"]
        except KeyError:
            pass

        try:
            header_dict = sub_json_dict["functional_header_info"]
        except KeyError:
            pass

        for qap_type in qap_types:
            try:
                qap_dict = sub_json_dict[qap_type]
            except KeyError:
                continue

            for key in sub_json_dict.keys():
                if "anatomical" not in key and "functional" not in key:
                    qap_dict[key] = sub_json_dict[key]

            qap_dict.update(header_dict)

            try:
                output_dict[qap_type].append(qap_dict)
            except KeyError:
                output_dict[qap_type] = [qap_dict]

    for qap_type in output_dict.keys():

        json_df = pd.DataFrame(output_dict[qap_type])
        json_df.sort_values(by=["Participant", "Session", "Series"],
                            inplace=True)
        if not csv_output_dir:
            csv_output_dir = os.getcwd()
        csv_file = os.path.join(csv_output_dir, "qap_{0}.csv".format(qap_type))

        json_df.to_csv(csv_file)
        print("CSV file created successfully: {0}".format(csv_file))

    return csv_file


def qap_csv_correlations(data_old, data_new, replacements=None):
    """Create a dictionary of correlations between old and new versions of 
    each QAP measure for the purpose of regression testing, for the 
    'qap_test_correlations.py' script.

    - This is for the 'qap_test_correlations.py' script.
    - This is intended for regression testing between versions of the QAP
      software.
    - The 'metric_list' below must be kept current with changes to metrics
      and their titles.

    :type data_old: Pandas DataFrame
    :param data_old: A DataFrame of QAP output measures from the older-
                     version run.
    :type data_new: Pandas DataFrame
    :param data_new: A DataFrame of QAP output measures from the newer-
                     version run.
    :type replacements: list
    :param replacements: A list of strings describing column name
                         replacements, in case column names have changed;
                         these strings are in the format "old_name,new_name".
    :rtype: dict
    :return: A dictionary of correlations values keyed by each QAP metric.
    """

    import pandas as pd
    import scipy.stats

    metric_list = ["EFC", "SNR", "FBER", "CNR", "FWHM", "Qi1", "Cortical Contrast",
                   "Ghost_x", "Ghost_y", "Ghost_z", "GCOR", "RMSD (Mean)",
                   "Quality (Mean)", "Fraction of Outliers (Mean)", "Std. DVARS (Mean)",
                   "Fraction of OOB Outliers (Mean)"]

    # update datasets if necessary
    if replacements:
        replace_dict = {}
        for word_couple in replacements:
            if "," not in word_couple:
                err = "\n\n[!] In the replacements text file, the old " \
                      "substring and its replacement must be separated " \
                      "by a comma.\n\nLine: {}\n\n".format(word_couple)
                raise Exception(err)
            word = word_couple.split(",")[0]
            new = word_couple.split(",")[1]
            replace_dict[word] = new

        data_old.rename(columns=replace_dict, inplace=True)
        data_new.rename(columns=replace_dict, inplace=True)

    # remove nulls
    data_old = data_old[pd.notnull(data_old["Participant"])]
    data_new = data_new[pd.notnull(data_new["Participant"])]

    for metric in metric_list:
        if metric in data_old:
            data_old = data_old[pd.notnull(data_old[metric])]
        if metric in data_new:
            data_new = data_new[pd.notnull(data_new[metric])]

    # make sure participant IDs are strings (if they are all digits, can be
    # mistakenly read in as ints or floats)
    if data_old["Participant"].dtype != str:
        try:
            # TODO: This is confusing, why is this needed?
            data_old["Participant"] = data_old["Participant"].astype(
                int).astype(str)
        except ValueError:
            data_old["Participant"] = data_old["Participant"].astype(str)

    if data_new["Participant"].dtype != str:
        try:
            data_new["Participant"] = data_new["Participant"].astype(
                int).astype(str)
        except ValueError:
            data_new["Participant"] = data_new["Participant"].astype(str)

    # make sure both DFs match
    data_merged = pd.merge(data_old, data_new,
                           on=["Participant", "Session", "Series"],
                           how="inner",
                           suffixes=("_OLD", "_NEW"))

    if len(data_merged) == 0:
        # try a last-ditch approach
        # TODO: This is confusing, why is this needed?
        try:
            data_old["Participant"] = data_old["Participant"].astype(int)
            data_new["Participant"] = data_new["Participant"].astype(int)
            data_merged = pd.merge(data_old, data_new,
                                   on=["Participant", "Session", "Series"],
                                   how="inner",
                                   suffixes=("_OLD", "_NEW"))
        except TypeError:
            pass
        if len(data_merged) == 0:
            err = "[!] There were no participant matches between the two " \
                  "CSVs."
            raise Exception(err)

    # correlate the numbers!
    correlations_dict = {}
    for metric in metric_list:
        metric_old = "_".join([metric, "OLD"])
        metric_new = "_".join([metric, "NEW"])
        if (metric_old in data_merged) and (metric_new in data_merged):
            metric_old_val = data_merged[metric_old]
            metric_new_val = data_merged[metric_new]
            correlations_dict[metric] = scipy.stats.pearsonr(metric_old_val,
                                                             metric_new_val)

    return correlations_dict


def write_inputs_dict_to_yaml_file(input_dict, yaml_outpath):
    """Write a participant data dictionary to a YAML file.

    - This is used across the participant list generator scripts.
    - yaml_outpath should also include the YAML filename.

    :type input_dict: dict
    :param input_dict: A participant data dictionary keyed by participant
                       information.
    :type yaml_outpath: str
    :param yaml_outpath: The filepath where to write the YAML file to.
    """

    import os
    import yaml         

    yaml_outpath = os.path.abspath(yaml_outpath)
    if (".yml" not in yaml_outpath) and (".yaml" not in yaml_outpath):
        yaml_outpath += ".yml"

    # write yaml file
    try:
        with open(yaml_outpath, "wt") as f:
            f.write(yaml.dump(input_dict))
    except OSError:
        err = "\n\n[!] Error writing YAML file output.\n1. Do you have " \
              "write permissions for the output path provided?\n2. Did you " \
              "provide a full path for the output path? Example: /home/data" \
              "/sublist.yml\n\nOutput path provided: {0}\n\n".format(yaml_outpath)
        raise Exception(err)
        
    if os.path.isfile(yaml_outpath):
        print("\nInputs dictionary file successfully created: {0}\n".format(yaml_outpath))
    else:
        err = "\n[!] Filepaths from the have not been successfully saved to the YAML file!\n" \
              "Output filepath: {}\n".format(yaml_outpath)
        raise Exception(err)


def check_csv_missing_subs(csv_df, data_dict, data_type):
    """Check which participant-sessions in the data configuration file didn't
    make it to the output CSV.

    - This is used in the qap_check_output_csv.py script.

    :type csv_df: Pandas DataFrame
    :param csv_df: A Pandas DataFrame object containing the information from
                   a QAP output CSV file.
    :type data_dict: dict
    :param data_dict: A QAP data configuration/resource pool dictionary.
    :type data_type: str
    :param data_type: The type of data- either 'anat' or 'func'.
    :rtype: dict
    :returns: A new data configuration dictionary containing the raw data
              filepaths of the participant data that didn't make it into the
              output CSV.
    """

    if data_type != "anat" and data_type != "func":
        err = "\n[!] data_type parameter must be either 'anat' or 'func'\n"
        raise Exception(err)

    scan_type = "anatomical_scan"
    if data_type == "func":
        scan_type = "functional_scan"

    uniques = []
    for sub in data_dict.keys():
        for ses in data_dict[sub].keys():
            if scan_type not in data_dict[sub][ses].keys():
                continue
            for scan in data_dict[sub][ses][scan_type].keys():
                uniques.append((sub, ses, scan))

    df_ids = csv_df[["Participant", "Session", "Series"]]
    df_uniques = [tuple(x) for x in df_ids.values]

    missing = list(set(uniques) - set(df_uniques))

    if len(missing) > 0:
        print("\n{0} scans missing in the output CSV compared to the input data config file.".format(len(missing)))
        # create subset of missing subs from input data config
        new_data = {}
        for data_id in missing:
            sub = data_id[0]
            ses = data_id[1]
            scan = data_id[2]
            if sub not in new_data.keys():
                new_data[sub] = {}
            if ses not in new_data[sub].keys():
                new_data[sub][ses] = {}
            if type not in new_data[sub][ses].keys():
                new_data[sub][ses][type] = {}
            if scan not in new_data[sub][ses][scan_type].keys():
                new_data[sub][ses][scan_type][scan] = \
                    data_dict[sub][ses][scan_type][scan]
        return new_data

    else:
        print("\nThe output CSV and input data config file match.")
        return None
