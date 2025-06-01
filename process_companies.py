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

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        pd.DataFrame: The loaded DataFrame, or an empty DataFrame if an error occurs.
    """
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return pd.DataFrame()
    except Exception as e: # Catching other potential read errors
        print(f"An error occurred while reading the CSV file '{filepath}': {e}")
        return pd.DataFrame()

def process_siren_siret(df: pd.DataFrame, siren_siret_col_name: str) -> pd.DataFrame:
    """
    Processes SIREN and SIRET numbers from a specified column in the DataFrame.
    It identifies whether an entry is a SIREN (9 digits) or SIRET (14 digits),
    extracts the SIREN part from SIRETs, and flags invalid entries.

    Args:
        df (pd.DataFrame): The input DataFrame.
        siren_siret_col_name (str): The name of the column containing SIREN/SIRET numbers.

    Returns:
        pd.DataFrame: The DataFrame with added columns: 'siren-siret-invalide',
                      'siren', and 'Siret'.
    """
    if siren_siret_col_name not in df.columns:
        print(f"Error: Column '{siren_siret_col_name}' not found for SIREN/SIRET processing. Creating empty result columns.")
        df['siren-siret-invalide'] = pd.NA
        df['siren'] = pd.NA
        df['Siret'] = pd.NA
        return df

    # Initialize new columns
    df['siren-siret-invalide'] = pd.NA
    df['siren'] = pd.NA
    df['Siret'] = pd.NA

    # Ensure the target column is of string type and values are stripped strings
    df[siren_siret_col_name] = df[siren_siret_col_name].astype(str).str.strip()

    def process_siren_row(value_str: str):
        """Helper function to process a single SIREN/SIRET string."""
        siren_siret_invalide = pd.NA
        siren = pd.NA
        siret_val = pd.NA

        if value_str.isdigit(): # Check if the string contains only digits
            if len(value_str) == 9:
                siren = value_str
            elif len(value_str) == 14:
                siret_val = value_str
                siren = value_str[:9] # Extract SIREN from SIRET
            else:
                siren_siret_invalide = "KO" # Invalid length
        # Handle cases like 'nan' string, empty string, or whitespace only string
        elif value_str.lower() == 'nan' or value_str == '' or value_str.isspace():
             siren_siret_invalide = "KO"
        else: # Non-digit strings are invalid
            siren_siret_invalide = "KO"

        return siren_siret_invalide, siren, siret_val

    # Apply the processing function row-wise
    results = df[siren_siret_col_name].apply(process_siren_row)
    df['siren-siret-invalide'] = results.apply(lambda x: x[0])
    df['siren'] = results.apply(lambda x: x[1])
    df['Siret'] = results.apply(lambda x: x[2])

    return df

def normalize_text(text: str) -> str:
    """
    Normalizes a text string by converting to uppercase, removing accents,
    removing special characters (allowing only alphanumeric and spaces),
    and stripping extra whitespace.

    Args:
        text (str): The input string to normalize.

    Returns:
        str: The normalized string. Returns an empty string if input is not a string.
    """
    if not isinstance(text, str): # Handles NaN, float, etc.
        return ""

    text = text.upper() # Convert to uppercase
    text = unidecode(text) # Remove accents (e.g., É -> E)
    text = re.sub(r'[^A-Z0-9\s]', '', text) # Remove special characters
    text = re.sub(r'\s+', ' ', text) # Replace multiple spaces with a single space
    return text.strip() # Strip leading/trailing whitespace

def normalize_company_name(df: pd.DataFrame, company_name_col: str, normalized_col_name: str) -> pd.DataFrame:
    """
    Normalizes company names in a DataFrame by applying text normalization
    and removing standard French legal terms.

    Args:
        df (pd.DataFrame): The input DataFrame.
        company_name_col (str): The name of the column containing company names.
        normalized_col_name (str): The name for the new column with normalized names.

    Returns:
        pd.DataFrame: The DataFrame with the added normalized company name column.
    """
    if company_name_col not in df.columns:
        print(f"Error: Column '{company_name_col}' not found for company name normalization. Creating empty '{normalized_col_name}'.")
        df[normalized_col_name] = ""
        return df

    # Apply basic text normalization, ensuring input is treated as string
    df[normalized_col_name] = df[company_name_col].astype(str).apply(normalize_text)

    # Remove legal terms using regex for whole word matching
    for term in UPPER_LEGAL_TERMS:
        df[normalized_col_name] = df[normalized_col_name].str.replace(r'\b' + re.escape(term) + r'\b', '', regex=True)

    # Clean up extra spaces that might result from removals
    df[normalized_col_name] = df[normalized_col_name].str.replace(r'\s+', ' ', regex=True).str.strip()
    return df

def normalize_address(df: pd.DataFrame, address_col: str, normalized_col_name: str) -> pd.DataFrame:
    """
    Normalizes addresses in a DataFrame by applying text normalization
    and replacing common French address abbreviations with their full forms.

    Args:
        df (pd.DataFrame): The input DataFrame.
        address_col (str): The name of the column containing addresses.
        normalized_col_name (str): The name for the new column with normalized addresses.

    Returns:
        pd.DataFrame: The DataFrame with the added normalized address column.
    """
    if address_col not in df.columns:
        print(f"Error: Column '{address_col}' not found for address normalization. Creating empty '{normalized_col_name}'.")
        df[normalized_col_name] = ""
        return df

    # Apply basic text normalization, ensuring input is treated as string
    df[normalized_col_name] = df[address_col].astype(str).apply(normalize_text)

    # Replace address abbreviations using regex for whole word matching
    for abbr, full_form in UPPER_ADDRESS_ABBREVIATIONS.items():
        df[normalized_col_name] = df[normalized_col_name].str.replace(r'\b' + re.escape(abbr) + r'\b', full_form, regex=True)

    # Clean up extra spaces
    df[normalized_col_name] = df[normalized_col_name].str.replace(r'\s+', ' ', regex=True).str.strip()
    return df

def deduplicate_by_siret(df: pd.DataFrame, siret_col: str, group_col_name: str) -> pd.DataFrame:
    """
    Identifies duplicate rows based on a SIRET column and assigns a group number
    to sets of duplicate SIRETs. Non-duplicates get NA in the group column.

    Args:
        df (pd.DataFrame): The input DataFrame.
        siret_col (str): The name of the column containing SIRET numbers.
        group_col_name (str): The name for the new column indicating duplicate groups.

    Returns:
        pd.DataFrame: The DataFrame with the added SIRET duplicate group column.
    """
    if siret_col not in df.columns:
        print(f"Error: Column '{siret_col}' not found for SIRET deduplication. Creating empty '{group_col_name}'.")
        df[group_col_name] = pd.NA
        return df

    df[group_col_name] = pd.NA # Initialize group column
    valid_sirets_mask = df[siret_col].notna() & (df[siret_col] != '')

    if valid_sirets_mask.any(): # Proceed only if there are any valid SIRETs
        duplicated_siret_series = df.loc[valid_sirets_mask, siret_col].duplicated(keep=False)
        duplicated_indices = df.loc[valid_sirets_mask][duplicated_siret_series].index

        if not duplicated_indices.empty:
            df.loc[duplicated_indices, group_col_name] = pd.factorize(df.loc[duplicated_indices, siret_col])[0] + 1
    return df

def deduplicate_by_siren(df: pd.DataFrame, siren_col: str, group_col_name: str) -> pd.DataFrame:
    """
    Identifies duplicate rows based on a SIREN column and assigns a group number
    to sets of duplicate SIRENs. Non-duplicates get NA in the group column.

    Args:
        df (pd.DataFrame): The input DataFrame.
        siren_col (str): The name of the column containing SIREN numbers.
        group_col_name (str): The name for the new column indicating duplicate groups.

    Returns:
        pd.DataFrame: The DataFrame with the added SIREN duplicate group column.
    """
    if siren_col not in df.columns:
        print(f"Error: Column '{siren_col}' not found for SIREN deduplication. Creating empty '{group_col_name}'.")
        df[group_col_name] = pd.NA
        return df

    df[group_col_name] = pd.NA
    valid_sirens_mask = df[siren_col].notna() & (df[siren_col] != '')

    if valid_sirens_mask.any():
        duplicated_siren_series = df.loc[valid_sirens_mask, siren_col].duplicated(keep=False)
        duplicated_indices = df.loc[valid_sirens_mask][duplicated_siren_series].index

        if not duplicated_indices.empty:
            df.loc[duplicated_indices, group_col_name] = pd.factorize(df.loc[duplicated_indices, siren_col])[0] + 1
    return df

def deduplicate_by_name_address(df: pd.DataFrame, name_col: str, address_col: str, group_col_name: str) -> pd.DataFrame:
    """
    Identifies duplicate rows based on normalized company name and address,
    assigns a group number to duplicate sets. Non-duplicates get NA.

    Args:
        df (pd.DataFrame): The input DataFrame.
        name_col (str): Name of the normalized company name column.
        address_col (str): Name of the normalized address column.
        group_col_name (str): Name for the new column indicating duplicate groups.

    Returns:
        pd.DataFrame: The DataFrame with the added name/address duplicate group column.
    """
    if name_col not in df.columns or address_col not in df.columns:
        print(f"Error: Columns '{name_col}' or '{address_col}' not found for name/address deduplication. Creating empty '{group_col_name}'.")
        df[group_col_name] = pd.NA
        return df

    df[group_col_name] = pd.NA
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
    """
    Saves the DataFrame to a CSV file.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        output_filepath (str): The path to the output CSV file.
    """
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
    This includes loading, SIREN/SIRET processing, data normalization (name, address),
    deduplication, and saving the processed data.
    If test_data_csv_string is provided, it's used instead of file loading, and saving is skipped.

    Args:
        input_filepath (str): Path to the input CSV file (used if test_data_csv_string is None).
        output_filepath (str): Path for the processed output CSV file (used if test_data_csv_string is None).
        test_data_csv_string (str, optional): A CSV string to use as input for testing. Defaults to None.

    Returns:
        pd.DataFrame | None: The processed DataFrame, or None if loading failed.
    """
    siren_siret_column_raw = "sien-siret"
    company_name_column_raw = "nom_entreprise"
    address_column_raw = "adresse_postale"

    if test_data_csv_string:
        print("Loading data from test_data_csv_string...")
        try:
            companies_df = pd.read_csv(io.StringIO(test_data_csv_string))
        except Exception as e:
            print(f"Error reading test_data_csv_string: {e}")
            return None
    else:
        companies_df = load_data(input_filepath)

    if companies_df.empty:
        print(f"Stopping processing as data loading failed or resulted in an empty DataFrame.")
        return None

    print("Data loaded successfully!")

    companies_df = process_siren_siret(companies_df, siren_siret_column_raw)

    if company_name_column_raw in companies_df.columns:
        companies_df[company_name_column_raw] = companies_df[company_name_column_raw].astype(str)
    companies_df = normalize_company_name(companies_df, company_name_column_raw, "nom_entreprise_normalise")

    if address_column_raw in companies_df.columns:
        companies_df[address_column_raw] = companies_df[address_column_raw].astype(str)
    companies_df = normalize_address(companies_df, address_column_raw, "adresse_normalisee")

    companies_df = deduplicate_by_siret(companies_df, "Siret", "groupe_doublon_siret")
    companies_df = deduplicate_by_siren(companies_df, "siren", "groupe_doublon_siren")
    companies_df = deduplicate_by_name_address(companies_df, "nom_entreprise_normalise",
                                               "adresse_normalisee", "groupe_doublon_nom_adresse")

    if 'siren' in companies_df.columns:
         companies_df.sort_values(by=['siren', 'Siret'], inplace=True, na_position='last') # Sort for consistent output

    print("\nProcessed DataFrame head (with deduplication groups):")
    cols_to_show = [
        siren_siret_column_raw, 'siren', 'Siret', 'siren-siret-invalide',
        company_name_column_raw, 'nom_entreprise_normalise',
        address_column_raw, 'adresse_normalisee',
        'groupe_doublon_siret', 'groupe_doublon_siren', 'groupe_doublon_nom_adresse'
    ]
    existing_cols_to_show = [col for col in cols_to_show if col in companies_df.columns]
    if existing_cols_to_show:
        print(companies_df[existing_cols_to_show].head())

    if not test_data_csv_string: # Only save if not in test mode
        save_data(companies_df, output_filepath)

    return companies_df

# --- Script Execution (Test Run) ---
if __name__ == "__main__":
    SAMPLE_CSV_DATA = """nom_entreprise,adresse_postale,sien-siret
"Alpha SARL","10 BD du Général Leclerc, 75001 Paris","123456789"
"Beta EURL","25 AV Foch, Lyon 69006","98765432109876"
"Gamma SA","10 Boulevard du Général Leclerc, 75001 PARIS","123456789"
"Delta SAS","5 Rue de la Paix, 75002 Paris","111222333"
"Alpha S.A.R.L.","10 BD du Général Leclerc, 75001 Paris","123456789"
"Epsilon & Co","33 CHE des Peupliers, 31000 Toulouse","ABC123456"
"Zeta Corp","N/A","999888777"
"Eta Ltd","50 Quai des Chartrons, Bordeaux 33000","98765432109876"
"Theta Inc.","25 Avenue Foch, 69006 Lyon","invalid_siret_length"
"Iota Solutions","1 Bis Impasse des Artistes, 06000 Nice","222333444"
"Kappa Services","1 BIS Impasse des Artistes, 06000 Nice","22233344400001"
"Lambda Systems"," inconnu ","555666777"
"Mu Holding","10 BD GÉNÉRAL LECLERC Paris 1er","123456789"
"Nu SARL", "123 Main St", "123456789012345"
"""
    print("--- Starting Test Run with In-Memory Sample Data ---")
    processed_df = main(test_data_csv_string=SAMPLE_CSV_DATA)

    if processed_df is not None:
        print("\n--- Full Processed DataFrame (CSV Output for Report) ---")
        # This output will be captured for the subtask report
        print(processed_df.to_csv(index=False))
        print("--- End of Test Run ---")
    else:
        print("--- Test Run Failed: No DataFrame was processed. ---")
