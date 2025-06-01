# Version 1 permettant de dédoublonner les lignes du fichier. Version 1 avant la version suivante avec l'appel à l'API SIREN
# Import necessary libraries
import pandas as pd
from unidecode import unidecode
import re
import io # Required for StringIO

# --- Constants for Normalization ---
LEGAL_TERMS = [
    'EURL', 'SARL', 'SA', 'SAS', 'SASU', 'SCI', 'SNC', 'SELARL', 'SELAS',
    'SELAFA', 'SCP', 'GAEC', 'EARL', 'GEIE', 'GIE', 'EI'
]
UPPER_LEGAL_TERMS = [term.upper() for term in LEGAL_TERMS] # For case-insensitive matching

ADDRESS_ABBREVIATIONS = {
    'BD': 'BOULEVARD', 'AV': 'AVENUE', 'RTE': 'ROUTE', 'CHE': 'CHEMIN',
    'PL': 'PLACE', 'TSSE': 'TERRASSE', 'QUA': 'QUAI', 'IMP': 'IMPASSE',
    'ALL': 'ALLEE', 'CRS': 'COURS', 'FG': 'FAUBOURG', 'ST': 'SAINT',
    'STE': 'SAINTE', 'CS': 'COURS', 'ZA': 'ZONE ARTISANALE',
    'ZI': 'ZONE INDUSTRIELLE', 'ZAC': 'ZONE AMENAGEMENT CONCERTE',
    'LOT': 'LOTISSEMENT', 'RES': 'RESIDENCE', 'BAT': 'BATIMENT',
    'ETG': 'ETAGE', 'NUM': 'NUMERO', 'LD': 'LIEU DIT', 'BP': 'BOITE POSTALE',
    'CEDEX': 'COURRIER ENTREPRISE DISTRIBUTION EXCEPTIONNELLE'
}
UPPER_ADDRESS_ABBREVIATIONS = {k.upper(): v.upper() for k, v in ADDRESS_ABBREVIATIONS.items()} # For case-insensitive matching

# --- Data Processing Functions ---

def load_data(filepath: str) -> pd.DataFrame:
    """
    Loads data from a CSV file into a pandas DataFrame.
    """
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred while reading the CSV file '{filepath}': {e}")
        return pd.DataFrame()

def process_siren_siret(df: pd.DataFrame,
                        tax_num1_col: str, tax_num2_col: str,
                        vat_reg_no_col: str, tax_number_generic_col: str,
                        output_siren_col: str, output_siret_col: str,
                        output_invalid_col: str, output_source_col: str) -> pd.DataFrame:
    """
    Extracts SIREN and SIRET numbers from multiple potential tax columns based on a priority order.
    """
    source_cols_to_check = [tax_num1_col, tax_num2_col, vat_reg_no_col, tax_number_generic_col]
    for col in source_cols_to_check:
        if col not in df.columns:
            print(f"Warning: Tax column '{col}' not found in DataFrame for SIREN/SIRET processing. It will be treated as empty.")
            df[col] = ''
        df[col] = df[col].astype(str).fillna('')


    def _clean_and_validate_id(value: str, expected_length: int) -> str | None:
        cleaned_value = str(value).strip()
        if cleaned_value.endswith(".0"):
            cleaned_value = cleaned_value[:-2]

        if cleaned_value.isdigit() and len(cleaned_value) == expected_length:
            return cleaned_value
        return None

    tva_regex = re.compile(r"^(?:FR|fr)[A-Za-z0-9]{2}(\d{9})$", re.IGNORECASE)

    def extract_siren_info_row(row):
        siren_val = pd.NA
        siret_val = pd.NA
        source_val = pd.NA
        is_invalid = pd.NA

        val_tax1 = row[tax_num1_col]
        siren_cand = _clean_and_validate_id(val_tax1, 9)
        if siren_cand:
            siren_val = siren_cand
            source_val = tax_num1_col
        else:
            siret_cand = _clean_and_validate_id(val_tax1, 14)
            if siret_cand:
                siret_val = siret_cand
                siren_val = siret_cand[:9]
                source_val = tax_num1_col

        if pd.isna(siren_val):
            val_tax2 = row[tax_num2_col]
            siren_cand = _clean_and_validate_id(val_tax2, 9)
            if siren_cand:
                siren_val = siren_cand
                source_val = tax_num2_col
            else:
                siret_cand = _clean_and_validate_id(val_tax2, 14)
                if siret_cand:
                    siret_val = siret_cand
                    siren_val = siret_cand[:9]
                    source_val = tax_num2_col

        if pd.isna(siren_val):
            val_vat = row[vat_reg_no_col].strip()
            match = tva_regex.match(val_vat)
            if match:
                siren_cand = match.group(1)
                if _clean_and_validate_id(siren_cand, 9):
                     siren_val = siren_cand
                     source_val = vat_reg_no_col

        if pd.isna(siren_val):
            val_tax_generic = row[tax_number_generic_col].strip()
            match = tva_regex.match(val_tax_generic)
            if match:
                siren_cand = match.group(1)
                if _clean_and_validate_id(siren_cand, 9):
                    siren_val = siren_cand
                    source_val = tax_number_generic_col

        if pd.isna(siren_val) and pd.isna(siret_val):
            is_invalid = "KO"
            all_sources_were_empty_originally = not (row[tax_num1_col] or \
                                     row[tax_num2_col] or \
                                     row[vat_reg_no_col] or \
                                     row[tax_number_generic_col])
            if all_sources_were_empty_originally:
                is_invalid = pd.NA
        return pd.Series([siren_val, siret_val, is_invalid, source_val])

    df[[output_siren_col, output_siret_col, output_invalid_col, output_source_col]] = \
        df.apply(extract_siren_info_row, axis=1)
    return df

def normalize_text(text: str) -> str:
    """
    Normalizes a text string by converting to uppercase, removing accents,
    removing special characters (allowing only alphanumeric and spaces),
    and stripping extra whitespace.
    """
    if not isinstance(text, str):
        return ""
    text = text.upper()
    text = unidecode(text)
    text = re.sub(r'[^A-Z0-9\s\.]', '', text)
    text = re.sub(r'\s+', ' ', text)
    tokens = text.split(' ')
    cleaned_tokens = []
    for token in tokens:
        if token.endswith(".0") and token[:-2].isdigit():
            cleaned_tokens.append(token[:-2])
        elif token == ".0":
             cleaned_tokens.append("0")
        else:
            cleaned_tokens.append(token)
    text = " ".join(cleaned_tokens)
    text = re.sub(r'\s\.\s', ' ', text)
    text = re.sub(r'^\.\s', '', text)
    text = re.sub(r'\s\.$', '', text)
    text = re.sub(r'\.+', '.', text)
    text = text.replace('.', '')
    return text.strip()

def normalize_company_name(df: pd.DataFrame, company_name_col: str, normalized_col_name: str) -> pd.DataFrame:
    """
    Normalizes company names in a DataFrame by applying text normalization
    and removing standard French legal terms.
    """
    if company_name_col not in df.columns:
        print(f"Warning: Column '{company_name_col}' not found for company name normalization. Output column '{normalized_col_name}' will remain empty.")
        df[normalized_col_name] = ""
        return df

    df[normalized_col_name] = df[company_name_col].astype(str).fillna('').apply(normalize_text)
    for term in UPPER_LEGAL_TERMS:
        df[normalized_col_name] = df[normalized_col_name].str.replace(r'\b' + re.escape(term) + r'\b', '', regex=True)
    df[normalized_col_name] = df[normalized_col_name].str.replace(r'\s+', ' ', regex=True).str.strip()
    return df

def normalize_address(df: pd.DataFrame,
                      po_box_col: str, street_col: str, postal_code_col: str,
                      city_col: str, region_col: str, country_col: str,
                      output_full_address_col: str,
                      output_normalized_address_col: str) -> pd.DataFrame:
    """
    Concatenates address components into a full address, then normalizes this full address.
    """
    address_component_cols = [po_box_col, street_col, postal_code_col, city_col, region_col]

    for col in address_component_cols:
        if col not in df.columns:
            print(f"Warning: Address component column '{col}' not found. It will be treated as empty.")
            df[col] = ''
        df[col] = df[col].astype(str).replace('nan', '', regex=False).fillna('')

    def concatenate_address_row(row):
        components = [
            row[po_box_col],
            row[street_col],
            row[postal_code_col],
            row[city_col],
            row[region_col]
        ]
        return " ".join(filter(None, components)).strip()

    df[output_full_address_col] = df.apply(concatenate_address_row, axis=1)
    df[output_normalized_address_col] = df[output_full_address_col].apply(normalize_text)

    for abbr, full_form in UPPER_ADDRESS_ABBREVIATIONS.items():
        df[output_normalized_address_col] = \
            df[output_normalized_address_col].str.replace(r'\b' + re.escape(abbr) + r'\b', full_form, regex=True)

    df[output_normalized_address_col] = \
        df[output_normalized_address_col].str.replace(r'\s+', ' ', regex=True).str.strip()
    return df

def deduplicate_by_siret(df: pd.DataFrame, siret_col: str, group_col_name: str) -> pd.DataFrame:
    """Identifies duplicate rows based on SIRET and assigns a group number."""
    if siret_col not in df.columns or df[siret_col].isnull().all():
        print(f"Warning: Column '{siret_col}' not found or all NA for SIRET deduplication. Group column '{group_col_name}' will remain empty.")
        if group_col_name not in df.columns: df[group_col_name] = pd.NA
        return df
    valid_sirets_mask = df[siret_col].notna() & (df[siret_col] != '')
    if valid_sirets_mask.any():
        duplicated_siret_series = df.loc[valid_sirets_mask, siret_col].duplicated(keep=False)
        duplicated_indices = df.loc[valid_sirets_mask][duplicated_siret_series].index
        if not duplicated_indices.empty:
            df.loc[duplicated_indices, group_col_name] = pd.factorize(df.loc[duplicated_indices, siret_col])[0] + 1
    return df

def deduplicate_by_siren(df: pd.DataFrame, siren_col: str, group_col_name: str) -> pd.DataFrame:
    """Identifies duplicate rows based on SIREN and assigns a group number."""
    if siren_col not in df.columns or df[siren_col].isnull().all():
        print(f"Warning: Column '{siren_col}' not found or all NA for SIREN deduplication. Group column '{group_col_name}' will remain empty.")
        if group_col_name not in df.columns: df[group_col_name] = pd.NA
        return df
    valid_sirens_mask = df[siren_col].notna() & (df[siren_col] != '')
    if valid_sirens_mask.any():
        duplicated_siren_series = df.loc[valid_sirens_mask, siren_col].duplicated(keep=False)
        duplicated_indices = df.loc[valid_sirens_mask][duplicated_siren_series].index
        if not duplicated_indices.empty:
            df.loc[duplicated_indices, group_col_name] = pd.factorize(df.loc[duplicated_indices, siren_col])[0] + 1
    return df

def deduplicate_by_name_address(df: pd.DataFrame, name_col: str, address_col: str, group_col_name: str) -> pd.DataFrame:
    """Identifies duplicate rows based on normalized name and address."""
    if name_col not in df.columns or address_col not in df.columns or \
       (df[name_col].isnull().all() and df[address_col].isnull().all()):
        print(f"Warning: Columns '{name_col}' or '{address_col}' not found or all NA for name/address deduplication. Group column '{group_col_name}' will remain empty.")
        if group_col_name not in df.columns: df[group_col_name] = pd.NA
        return df

    valid_entries_mask = (df[name_col].notna() & (df[name_col] != '')) & \
                         (df[address_col].notna() & (df[address_col] != ''))
    if valid_entries_mask.any():
        df_valid_subset = df[valid_entries_mask]
        if not df_valid_subset.empty:
            is_duplicated_name_address = df_valid_subset.duplicated(subset=[name_col, address_col], keep=False)
            duplicated_indices = df_valid_subset[is_duplicated_name_address].index
            if not duplicated_indices.empty:
                combined_key_series = df.loc[duplicated_indices, name_col] + "_@@_" + df.loc[duplicated_indices, address_col]
                df.loc[duplicated_indices, group_col_name] = pd.factorize(combined_key_series)[0] + 1
    return df

def save_data(df: pd.DataFrame, output_filepath: str) -> None:
    """Saves the DataFrame to a CSV file."""
    if df is None:
        print("Error: No DataFrame provided to save.")
        return
    if not isinstance(df, pd.DataFrame):
        print(f"Error: Provided data for saving is not a pandas DataFrame. Type: {type(df)}")
        return
    try:
        df.to_csv(output_filepath, index=False, encoding='utf-8')
        print(f"Successfully saved processed data to '{output_filepath}'")
    except IOError as e:
        print(f"IOError: Failed to save data to '{output_filepath}'. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving data to '{output_filepath}'. Error: {e}")

# --- Main Orchestration Function ---
def main(input_filepath: str = "french_companies.csv",
         output_filepath: str = "french_companies_processed.csv",
         test_data_csv_string: str = None) -> pd.DataFrame | None:
    """
    Main function to orchestrate the company data processing workflow.
    """
    col_supplier_name = "Supplier"
    col_address_street = "Street"
    col_address_city = "City"
    col_address_postal_code = "PostalCode"
    col_address_region = "Region"
    col_address_po_box = "PO Box"
    col_country = "Cty"
    col_tax_num1 = "Tax Number 1"
    col_tax_num2 = "Tax Number 2"
    col_vat_reg_no = "VAT Registration No."
    col_tax_number_generic = "Tax Number"

    out_col_siren_invalid = "siren-siret-invalide"
    out_col_siren = "siren"
    out_col_siret = "Siret"
    out_col_siren_source = "source_siren_siret"
    out_col_norm_name = "nom_entreprise_normalise"
    out_col_original_full_address = "adresse_complete_originale"
    out_col_norm_address = "adresse_normalisee"
    out_col_dup_group_siret = "groupe_doublon_siret"
    out_col_dup_group_siren = "groupe_doublon_siren"
    out_col_dup_group_name_address = "groupe_doublon_nom_adresse"

    if test_data_csv_string:
        print("Loading data from test_data_csv_string...")
        try:
            companies_df = pd.read_csv(io.StringIO(test_data_csv_string), quotechar='"', skipinitialspace=True, keep_default_na=False, na_filter=False)
        except Exception as e:
            print(f"Error reading test_data_csv_string: {e}")
            return None
    else:
        companies_df = load_data(input_filepath)

    if companies_df.empty:
        print(f"Stopping processing as data loading failed or resulted in an empty DataFrame.")
        return None
    print("Data loaded successfully!")

    expected_input_cols_for_main = [
        col_supplier_name, col_address_po_box, col_address_street, col_address_city,
        col_address_postal_code, col_address_region, col_country,
        col_tax_num1, col_tax_num2, col_vat_reg_no, col_tax_number_generic
    ]
    for col in expected_input_cols_for_main:
        if col not in companies_df.columns:
            print(f"Warning: Expected input column '{col}' not found. Adding as empty string column.")
            companies_df[col] = ''
        companies_df[col] = companies_df[col].fillna('').astype(str).replace('nan', '', regex=False).replace('NaN', '', regex=False)


    output_column_names = [
        out_col_siren_invalid, out_col_siren, out_col_siret, out_col_siren_source,
        out_col_norm_name, out_col_original_full_address, out_col_norm_address,
        out_col_dup_group_siret, out_col_dup_group_siren, out_col_dup_group_name_address
    ]
    for col_name in output_column_names:
        companies_df[col_name] = pd.NA

    companies_df = process_siren_siret(companies_df,
                                       col_tax_num1, col_tax_num2,
                                       col_vat_reg_no, col_tax_number_generic,
                                       out_col_siren, out_col_siret,
                                       out_col_siren_invalid, out_col_siren_source)

    companies_df = normalize_company_name(companies_df, col_supplier_name, out_col_norm_name)

    companies_df = normalize_address(companies_df,
                                     col_address_po_box, col_address_street,
                                     col_address_postal_code, col_address_city,
                                     col_address_region, col_country,
                                     out_col_original_full_address, out_col_norm_address)

    companies_df = deduplicate_by_siret(companies_df, out_col_siret, out_col_dup_group_siret)
    companies_df = deduplicate_by_siren(companies_df, out_col_siren, out_col_dup_group_siren)
    companies_df = deduplicate_by_name_address(companies_df, out_col_norm_name,
                                               out_col_norm_address, out_col_dup_group_name_address)

    if out_col_siren in companies_df.columns:
         companies_df.sort_values(by=[out_col_siren, out_col_siret], inplace=True, na_position='last')

    # This print statement is for when running in test mode or for general verbosity.
    # It might be too verbose for production file processing unless needed for a log.
    print("\nProcessed DataFrame head (final structure):")
    key_input_cols_for_display = [
        col_supplier_name, col_address_street, col_address_city, col_address_postal_code,
        col_tax_num1
    ]
    key_input_cols_for_display = [col for col in key_input_cols_for_display if col in companies_df.columns]
    all_cols_to_display = key_input_cols_for_display + output_column_names
    existing_display_cols = [col for col in all_cols_to_display if col in companies_df.columns]

    print(companies_df[existing_display_cols].head())

    if not test_data_csv_string:
        save_data(companies_df, output_filepath)
        print(f"File processing complete. Output saved to '{output_filepath}'.")

    return companies_df

# --- Script Execution ---
if __name__ == "__main__":
    # Default behavior: Process a CSV file as defined in main() defaults.
    # This will typically look for "french_companies.csv" and save "french_companies_processed.csv".
    print("Running in standard file processing mode.")
    main()

    # --- For testing with in-memory sample data ---
    # To run with the sample data string below, comment out the `main()` call above,
    # and uncomment the following lines:

    # print("\n--- Starting Test Run with Comprehensive Sample Data ---")
    # # Using a list of strings joined by newline for clarity and precise comma control.
    # # Each data line must have 10 commas for 11 fields.
    # # All empty fields are explicitly represented as "" for clarity with read_csv.
    # csv_lines = [
    #     "Supplier,PO Box,Street,City,PostalCode,Region,Cty,Tax Number 1,Tax Number 2,VAT Registration No.,Tax Number",
    #     '"Company A (SIREN TN1)","","1 Rue Principale","Paris","75001","IDF","FR","111111111","","FRXX111111111",""',
    #     '"Company B (SIRET TN1)","","2 Avenue Libération","Lyon","69002","ARA","FR","22222222222222","","FRYY222222222",""',
    #     '"Company C (SIREN TN2)","","3 Place Victoire","Bordeaux","33001","NAQ","FR","","333333333","FRZZ333333333",""',
    #     '"Company D (SIRET TN2)","","4 Boulevard Voltaire","Lille","59000","HDF","FR","","44444444444444","FRAA444444444",""',
    #     '"Company E (SIREN VAT)","","5 Chemin Vert","Nantes","44001","PDL","FR","invalid","invalid","FRBB555555555",""',
    #     '"Company F (SIREN GenTax)","","6 Allée Bleue","Strasbourg","67001","GE","FR","invalid","invalid","","FRCC666666666"',
    #     '"Company G (Invalid ID)","","7 Impasse Rouge","Nice","06001","PACA","FR","123","456","FRDD12345","badID"',
    #     '"Company H (Duplicate SIRET B)","","8 Rue Secondaire","Lyon","69002","ARA","FR","22222222222222","","FRYY222222222",""',
    #     '"Company A (Name/Addr Dup)","","1 Rue Principale","Paris","75001","IDF","FR","999111111","","",""',
    #     '"Company I (No Address)","","","","","","FR","777777777","","",""',
    #     '"Company J (Foreign)","","10 Downing Street","London","","UK","GB123456789","","","",""',
    #     '"Company K (SIREN .0)","","11 Rue Neuve","Paris","75010","IDF","FR","888888888.0","","",""'
    # ]
    # SAMPLE_CSV_DATA_NEW_FORMAT = "\n".join(csv_lines)
    # processed_df = main(test_data_csv_string=SAMPLE_CSV_DATA_NEW_FORMAT)
    # if processed_df is not None:
    #     print("\n--- Full Processed DataFrame (CSV Output for Final Report) ---")
    #     print(processed_df.to_csv(index=False))
    #     print("--- End of Final Test Run ---")
    # else:
    #     print("--- Final Test Run Failed: No DataFrame was processed. ---")
