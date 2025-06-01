import pandas as pd
import requests
import argparse
import time
import sys
import json

# Global variable for rate limiting
LAST_API_CALL_TIME = 0
INSEE_API_BASE_URL = "https://api.insee.fr/entreprises/sirene/V3.11"

NEW_INSEE_COLUMNS_DEFINITION = {
    "INSEE_SIRET": pd.NA, "INSEE_SIREN_UL": pd.NA,
    "INSEE_DenominationUniteLegale": pd.NA, "INSEE_DenominationUsuelleEtablissement": pd.NA,
    "INSEE_Adresse_Complete": pd.NA, "INSEE_CodePostalEtablissement": pd.NA,
    "INSEE_LibelleCommuneEtablissement": pd.NA, "INSEE_EstSiege": pd.NA,
    "INSEE_NumeroTVA": pd.NA, "INSEE_DateSuppressionUniteLegale": pd.NA,
    "INSEE_StatutAdministratifUL": pd.NA, "INSEE_EtatAdministratifEtablissement": pd.NA,
    "INSEE_CaractereEmployeurEtablissement": pd.NA,
    "Statut_API_INSEE": pd.NA
}

def ensure_api_rate_limit(min_interval_seconds: float = 2.0):
    """
    Ensures that calls to the API do not exceed a defined rate limit.
    Pauses execution if the time since the last call is less than min_interval_seconds.

    Args:
        min_interval_seconds (float): Minimum time interval between API calls in seconds.
                                      Default is 2.0 (approx. 30 calls per minute).
    """
    global LAST_API_CALL_TIME
    current_time = time.time()
    elapsed_time_since_last_call = current_time - LAST_API_CALL_TIME
    if elapsed_time_since_last_call < min_interval_seconds:
        sleep_duration = min_interval_seconds - elapsed_time_since_last_call
        # print(f"Rate limit: sleeping for {sleep_duration:.2f} seconds...") # Less verbose for final
        time.sleep(sleep_duration)
    LAST_API_CALL_TIME = time.time()

def call_insee_api(endpoint_url: str, api_token: str, params: dict = None) -> dict | None:
    """
    Calls the INSEE API with the specified endpoint, token, and parameters.
    Handles rate limiting, common HTTP errors, and JSON parsing.

    Args:
        endpoint_url (str): The full URL for the API endpoint.
        api_token (str): The API token for authorization.
        params (dict, optional): A dictionary of query parameters for the API call. Defaults to None.

    Returns:
        dict | None: The parsed JSON response if successful, None otherwise.
    """
    ensure_api_rate_limit()
    headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}

    # Prepare request for logging URL
    session = requests.Session()
    request = requests.Request('GET', endpoint_url, params=params, headers=headers)
    prepared_request = session.prepare_request(request) # Use session to prepare for consistency

    print(f"INFO: Calling API. Prepared URL: {prepared_request.url}")

    try:
        # Use the session to send the prepared request
        response = session.send(prepared_request, timeout=20)

        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                print(f"Error: Failed to parse JSON response from API for URL: {prepared_request.url}. Response text: {response.text[:200]}...")
                return None
        elif response.status_code == 401: print(f"API Erreur 401: Non autorisé (URL: {prepared_request.url}). Vérifiez token."); return None
        elif response.status_code == 403: print(f"API Erreur 403: Interdit (URL: {prepared_request.url}). Droits/Token invalide."); return None
        elif response.status_code == 404: print(f"API Erreur 404: Ressource non trouvée: {prepared_request.url}"); return None
        elif response.status_code == 429: print(f"API Erreur 429: Trop de requêtes (URL: {prepared_request.url})."); return None
        elif response.status_code == 400: print(f"API Erreur 400: Mauvaise requête (URL: {prepared_request.url}). Détails: {response.text}"); return None
        else: print(f"API Erreur {response.status_code} (URL: {prepared_request.url}). Réponse: {response.text[:200]}"); return None
    except requests.exceptions.Timeout: print(f"API Erreur: Timeout (20s) pour URL: {prepared_request.url}"); return None
    except requests.exceptions.RequestException as e: print(f"API Erreur de connexion (URL: {prepared_request.url}): {e}"); return None

def _build_complete_address(adresse_json: dict | None) -> str:
    """
    Constructs a single, complete address string from an INSEE API addressEtablissement object.

    Args:
        adresse_json (dict | None): The address object from the API response.

    Returns:
        str: A concatenated string of the address components, or an empty string if input is invalid.
    """
    if not adresse_json or not isinstance(adresse_json, dict): return ""
    parts = [
        adresse_json.get("numeroVoieEtablissement"),
        adresse_json.get("indiceRepetitionEtablissement"),
        adresse_json.get("typeVoieEtablissement"),
        adresse_json.get("libelleVoieEtablissement"),
        adresse_json.get("complementAdresseEtablissement"),
        adresse_json.get("codePostalEtablissement"),
        adresse_json.get("libelleCommuneEtablissement"),
        adresse_json.get("libelleCedexEtablissement")
    ]
    return " ".join(filter(None, [str(p).strip() for p in parts if p and str(p).strip()])).strip()

def parse_unite_legale_data(ul_json: dict | None) -> dict:
    """
    Parses relevant fields from the 'uniteLegale' JSON object from an API response.

    Args:
        ul_json (dict | None): The 'uniteLegale' object.

    Returns:
        dict: A dictionary containing parsed legal unit information with predefined keys.
    """
    if not ul_json or not isinstance(ul_json, dict): return {}
    parsed_ul = {}
    current_period_ul_list = ul_json.get("periodesUniteLegale")
    current_period_ul = current_period_ul_list[0] if isinstance(current_period_ul_list, list) and current_period_ul_list else ul_json

    parsed_ul["INSEE_SIREN_UL"] = ul_json.get("siren", pd.NA)
    parsed_ul["INSEE_DenominationUniteLegale"] = current_period_ul.get("denominationUniteLegale", ul_json.get("denominationUniteLegale", pd.NA))
    parsed_ul["INSEE_StatutAdministratifUL"] = current_period_ul.get("statutAdministratifUniteLegale", ul_json.get("statutAdministratifUniteLegale", pd.NA))
    parsed_ul["INSEE_DateSuppressionUniteLegale"] = current_period_ul.get("dateFin", ul_json.get("dateSuppressionUniteLegale", pd.NA))
    parsed_ul["INSEE_NumeroTVA"] = ul_json.get("numeroTvaIntracommunautaire", pd.NA)
    return parsed_ul

def parse_etablissement_data(etablissement_json: dict | None, ul_data_for_etab: dict = None) -> dict:
    """
    Parses relevant fields from an 'etablissement' JSON object from an API response.
    Optionally merges pre-parsed data from its parent legal unit.

    Args:
        etablissement_json (dict | None): The 'etablissement' object.
        ul_data_for_etab (dict, optional): Pre-parsed data from the parent legal unit.

    Returns:
        dict: A dictionary containing parsed establishment (and UL) information.
    """
    if not etablissement_json or not isinstance(etablissement_json, dict): return {}
    parsed_etab = {}

    if not ul_data_for_etab:
        ul_data_raw = etablissement_json.get("uniteLegale", {})
        ul_data_for_etab = parse_unite_legale_data(ul_data_raw)
    parsed_etab.update(ul_data_for_etab)

    parsed_etab["INSEE_SIRET"] = etablissement_json.get("siret", pd.NA)
    is_siege = etablissement_json.get("etablissementSiege")
    parsed_etab["INSEE_EstSiege"] = True if str(is_siege).lower() == 'true' else (False if str(is_siege).lower() == 'false' else pd.NA)

    current_period_etab_list = etablissement_json.get("periodesEtablissement")
    current_period_etab = current_period_etab_list[0] if isinstance(current_period_etab_list, list) and current_period_etab_list else etablissement_json

    parsed_etab["INSEE_DenominationUsuelleEtablissement"] = current_period_etab.get("denominationUsuelleEtablissement", pd.NA)
    if pd.isna(parsed_etab.get("INSEE_DenominationUsuelleEtablissement")) and parsed_etab.get("INSEE_DenominationUniteLegale"):
        parsed_etab["INSEE_DenominationUsuelleEtablissement"] = parsed_etab.get("INSEE_DenominationUniteLegale")

    adresse_obj = etablissement_json.get("adresseEtablissement", {})
    parsed_etab["INSEE_Adresse_Complete"] = _build_complete_address(adresse_obj)
    parsed_etab["INSEE_CodePostalEtablissement"] = adresse_obj.get("codePostalEtablissement", pd.NA)
    parsed_etab["INSEE_LibelleCommuneEtablissement"] = adresse_obj.get("libelleCommuneEtablissement", pd.NA)

    parsed_etab["INSEE_EtatAdministratifEtablissement"] = current_period_etab.get("etatAdministratifEtablissement", etablissement_json.get("etatAdministratifEtablissement", pd.NA))
    parsed_etab["INSEE_CaractereEmployeurEtablissement"] = current_period_etab.get("caractereEmployeurEtablissement", etablissement_json.get("caractereEmployeurEtablissement", pd.NA))
    return parsed_etab

def get_data_by_siret(siret: str, api_token: str) -> dict | None:
    """
    Retrieves and parses data for a specific SIRET from the INSEE API.
    Fetches the default full payload.
    """
    url = f"{INSEE_API_BASE_URL}/siret/{siret.strip()}"
    response_json = call_insee_api(url, api_token, params=None)
    if response_json and "etablissement" in response_json:
        etablissement_raw = response_json["etablissement"]
        ul_data_raw = etablissement_raw.get("uniteLegale", {})
        parsed_ul_data = parse_unite_legale_data(ul_data_raw)
        return parse_etablissement_data(etablissement_raw, parsed_ul_data)
    return None

def get_data_by_siren(siren: str, api_token: str) -> dict | None:
    """
    Retrieves and parses data for a specific SIREN from the INSEE API.
    Prioritizes data from the headquarters (siège) if found by fetching its full SIRET data.
    """
    url = f"{INSEE_API_BASE_URL}/siren/{siren.strip()}"
    response_json = call_insee_api(url, api_token, params=None)
    if response_json and "uniteLegale" in response_json:
        ul_data_raw = response_json["uniteLegale"]
        parsed_ul_data = parse_unite_legale_data(ul_data_raw)

        siege_etablissement_raw = None
        etablissements_list = ul_data_raw.get("etablissements", [])
        for etab_raw_item in etablissements_list:
            if str(etab_raw_item.get("etablissementSiege", "false")).lower() == 'true':
                siege_etablissement_raw = etab_raw_item; break

        if siege_etablissement_raw and siege_etablissement_raw.get("siret"):
            print(f"Info: Siege found for SIREN {siren}, SIRET: {siege_etablissement_raw.get('siret')}. Fetching its full details.")
            siege_siret = siege_etablissement_raw.get('siret')
            # Fetch full siege details using its SIRET
            siege_details = get_data_by_siret(siege_siret, api_token)
            if siege_details:
                final_data = parsed_ul_data.copy()
                final_data.update(siege_details)
                return final_data
            else:
                print(f"Warning: Failed to fetch full details for siege SIRET {siege_siret}. Using partial data from SIREN call for siege.")
                return parse_etablissement_data(siege_etablissement_raw, parsed_ul_data)
        else:
            parsed_data = parsed_ul_data
            if etablissements_list:
                 first_etab_raw = etablissements_list[0]
                 parsed_data["INSEE_SIRET"] = first_etab_raw.get("siret")
                 parsed_data["INSEE_Adresse_Complete"] = _build_complete_address(first_etab_raw.get("adresseEtablissement"))
                 parsed_data["INSEE_CodePostalEtablissement"] = first_etab_raw.get("adresseEtablissement",{}).get("codePostalEtablissement")
                 parsed_data["INSEE_LibelleCommuneEtablissement"] = first_etab_raw.get("adresseEtablissement",{}).get("libelleCommuneEtablissement")
                 parsed_data["INSEE_DenominationUsuelleEtablissement"] = first_etab_raw.get("denominationUsuelleEtablissement")
                 parsed_data["INSEE_EstSiege"] = False # Corrected from parsed_etab to parsed_data
            return parsed_data
    return None

def escape_lucene_value(value: str) -> str:
    """Escapes Lucene special characters in a search term value."""
    # Ensure value is a string before applying replace
    value_str = str(value)
    value_str = value_str.replace('\\', '\\\\')
    special_chars = ['+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '/']
    for char in special_chars:
        value_str = value_str.replace(char, f'\\{char}')
    return value_str

def search_data_by_name(normalized_name: str, api_token: str, only_active: bool = True) -> list[dict] | None:
    """
    Searches for establishments by name using the INSEE API.
    Uses a simplified query (denominationUniteLegale only) and applies client-side filtering for active status.

    Args:
        normalized_name (str): The normalized company name to search for.
        api_token (str): The API token.
        only_active (bool): If True, results are filtered client-side for active entities.

    Returns:
        list[dict] | None: A list of parsed establishment data dicts,
                           or None if API call error, or empty list if no matches.
    """
    base_url = f"{INSEE_API_BASE_URL}/siret"
    name_escaped = escape_lucene_value(normalized_name)

    # Final simplified query: search only on denominationUniteLegale.
    query_string = f'denominationUniteLegale:"{name_escaped}"'

    if only_active:
        print(f"Info: 'only_active=True' for name search '{normalized_name}'. Client-side filtering will be applied to results of query: q={query_string}")

    params = {"q": query_string}

    response_json = call_insee_api(base_url, api_token, params=params)

    if response_json and "etablissements" in response_json:
        all_results_parsed = []
        for etab_raw in response_json["etablissements"]:
            parsed_etab_data = parse_etablissement_data(etab_raw)
            all_results_parsed.append(parsed_etab_data)

        if only_active:
            active_results = []
            # print(f"Info: Applying client-side 'only_active' filter. Found {len(all_results_parsed)} raw results.") # Verbose
            for res in all_results_parsed:
                ul_status = res.get("INSEE_StatutAdministratifUL")
                etab_status = res.get("INSEE_EtatAdministratifEtablissement")
                if str(ul_status) == 'A' and str(etab_status) == 'A':
                    active_results.append(res)
                # else: # Verbose
                    # print(f"Info: Candidate SIRET {res.get('INSEE_SIRET')} for '{normalized_name}' filtered out (client-side) due to status (UL: {ul_status}, Etab: {etab_status})")
            # print(f"Info: Found {len(active_results)} active results after client-side filtering for '{normalized_name}'.")
            return active_results
        else:
            return all_results_parsed

    elif response_json and response_json.get("header", {}).get("total", 0) == 0: return []
    return None


def main():
    """Main execution flow: parse args, load data, process rows, save results."""
    parser = argparse.ArgumentParser(description="Enrich company data using INSEE SIRENE API.")
    parser.add_argument( "--input-file", "-i", required=True, help="Path to the input CSV file.")
    parser.add_argument( "--output-file", "-o", required=True, help="Path to save the enriched output CSV file.")
    parser.add_argument( "--api-token", "-t", required=True, help="API token for INSEE SIRENE API.")
    parser.add_argument( "--multiple-matches-file", "-m", required=True, help="Path to save CSV file for multiple matches found via name search.")
    args = parser.parse_args()

    masked_token = f"{'*' * (len(args.api_token) - 4)}{args.api_token[-4:]}" if len(args.api_token) > 4 else "***"
    print("--- Configuration ---"); print(f"Input File: {args.input_file}"); print(f"Output File: {args.output_file}"); print(f"API Token: {masked_token}"); print(f"Multiple Matches File: {args.multiple_matches_file}"); print("---------------------\n")

    col_input_siret = "Siret"; col_input_siren = "siren"; col_input_nom_normalise = "nom_entreprise_normalise"

    try: df = pd.read_csv(args.input_file, dtype=str, keep_default_na=False, na_filter=False)
    except FileNotFoundError: print(f"Erreur: Le fichier d'entrée '{args.input_file}' n'a pas été trouvé."); sys.exit(1)
    except Exception as e: print(f"Erreur lors de la lecture du fichier d'entrée '{args.input_file}': {e}"); sys.exit(1)
    print(f"Loaded {len(df)} rows from {args.input_file}")

    for col_name in NEW_INSEE_COLUMNS_DEFINITION.keys(): df[col_name] = pd.NA
    multiple_matches_accumulator = []

    print("Starting data enrichment process...")
    for index, row in df.iterrows():
        siret_val = str(row.get(col_input_siret, '')).strip()
        siren_val = str(row.get(col_input_siren, '')).strip()
        nom_val = str(row.get(col_input_nom_normalise, '')).strip()
        processed_data_for_row = None; status_msg = pd.NA

        if not siret_val and not siren_val and not nom_val: status_msg = "Aucun critère de recherche"
        else:
            if siret_val and len(siret_val) == 14 and siret_val.isdigit():
                # print(f"Row {index+1}: Querying by SIRET {siret_val}")
                processed_data_for_row = get_data_by_siret(siret_val, args.api_token)
                status_msg = "OK - SIRET" if processed_data_for_row else "INSEE: SIRET non trouvé/Erreur"

            if not processed_data_for_row and siren_val and len(siren_val) == 9 and siren_val.isdigit():
                # print(f"Row {index+1}: Querying by SIREN {siren_val}")
                processed_data_for_row = get_data_by_siren(siren_val, args.api_token)
                status_msg = "OK - SIREN" if processed_data_for_row else "INSEE: SIREN non trouvé/Erreur"

            if not processed_data_for_row and nom_val:
                # print(f"Row {index+1}: Querying by Name '{nom_val}'")
                search_results = search_data_by_name(nom_val, args.api_token, only_active=True)
                if search_results is not None:
                    if len(search_results) == 0: status_msg = "INSEE: Non trouvé par nom"
                    elif len(search_results) == 1: processed_data_for_row = search_results[0]; status_msg = "OK - Nom (1 résultat)"
                    else:
                        status_msg = f"INSEE: Plusieurs par nom ({len(search_results)} trouvés)"
                        multiple_matches_accumulator.append({'original_row_index': index,'original_data': row.to_dict(),'api_candidates': search_results})
                else: status_msg = "INSEE: Erreur recherche Nom"

            if pd.isna(status_msg) and processed_data_for_row is None and (siret_val or siren_val or nom_val) :
                status_msg = "Critères fournis invalides ou API inaccessible"

        if processed_data_for_row:
            for key, value in processed_data_for_row.items():
                if key in df.columns: df.loc[index, key] = value
        df.loc[index, "Statut_API_INSEE"] = status_msg
        if (index + 1) % 1 == 0 or (index + 1) == len(df):
            print(f"Processed {index + 1}/{len(df)} rows. Status: {status_msg}")

    print("\nEnrichment process completed.")
    try: df.to_csv(args.output_file, index=False, encoding='utf-8'); print(f"Enriched data saved to '{args.output_file}'")
    except Exception as e: print(f"Erreur lors de la sauvegarde du fichier de sortie principal: {e}")

    if multiple_matches_accumulator:
        print(f"\nFound {len(multiple_matches_accumulator)} rows with multiple matches (after client-side filtering if active). Preparing '{args.multiple_matches_file}'...")
        multiple_matches_df_rows = []
        for item in multiple_matches_accumulator:
            original_row_data = item['original_data']
            for candidate_data in item['api_candidates']:
                new_row = original_row_data.copy()
                new_row['original_row_index_in_input'] = item['original_row_index']
                for key, value in candidate_data.items(): new_row[f"{key}"] = value
                multiple_matches_df_rows.append(new_row)
        if multiple_matches_df_rows:
            multiple_df = pd.DataFrame(multiple_matches_df_rows)
            try: multiple_df.to_csv(args.multiple_matches_file, index=False, encoding='utf-8'); print(f"Multiple matches data saved to '{args.multiple_matches_file}'")
            except Exception as e: print(f"Erreur lors de la sauvegarde du fichier des correspondances multiples: {e}")
        else: print("No data to save for multiple matches (list was empty after processing, possibly due to client-side filtering).")
    else: print("No multiple matches found to save.")
    print("\nScript finished.")

if __name__ == "__main__":
    # Default behavior: Expect command-line arguments
    main()
```
