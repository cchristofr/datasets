import pandas as pd
import requests
import argparse
import time
import sys
import json
import os # Ajouté
import re # Ajouté

# --- Global Variables & Constants ---
LAST_API_CALL_TIME = 0
INSEE_API_BASE_URL = "https://api.insee.fr/entreprises/sirene/V3.11"

# Definition of new columns to be added to the DataFrame for INSEE data.
NEW_INSEE_COLUMNS_DEFINITION = {
    "INSEE_SIRET": pd.NA,
    "INSEE_SIREN_UL": pd.NA,
    "INSEE_DenominationUniteLegale": pd.NA,
    "INSEE_DenominationUsuelleEtablissement": pd.NA,
    "INSEE_Adresse_Complete": pd.NA,
    "INSEE_CodePostalEtablissement": pd.NA,
    "INSEE_LibelleCommuneEtablissement": pd.NA,
    "INSEE_EstSiege": pd.NA,
    "INSEE_NumeroTVA": pd.NA,
    "INSEE_DateSuppressionUniteLegale": pd.NA,
    "INSEE_StatutAdministratifUL": pd.NA,
    "INSEE_EtatAdministratifEtablissement": pd.NA,
    "INSEE_CaractereEmployeurEtablissement": pd.NA,
    "Statut_API_INSEE": pd.NA
}
# Champs à demander à l'API (utilisé par search_data_by_name_and_city, les autres utilisent None pour default)
DEFAULT_INSEE_FIELDS = [
    "siret", "siren", "etablissementSiege", "denominationUsuelleEtablissement",
    "etatAdministratifEtablissement", "caractereEmployeurEtablissement",
    "adresseEtablissement", # Pour obtenir l'objet adresse complet
    "denominationUniteLegale", "statutAdministratifUniteLegale",
    "dateSuppressionUniteLegale", "numeroTvaIntracommunautaire"
]


# --- Helper Functions ---

def escape_lucene_value(value: str) -> str:
    """
    Escapes Lucene special characters in a search term value.
    Special characters: + - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
    The backslash must be escaped first.
    """
    if not isinstance(value, str):
        return ""
    value = value.replace('\\', '\\\\')
    special_chars = ['+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '/']
    for char in special_chars:
        value = value.replace(char, f'\\{char}')
    return value

def ensure_api_rate_limit(min_interval_seconds: float = 2.0):
    """
    Ensures that calls to the API do not exceed a defined rate limit.
    """
    global LAST_API_CALL_TIME
    current_time = time.time()
    elapsed_time_since_last_call = current_time - LAST_API_CALL_TIME
    if elapsed_time_since_last_call < min_interval_seconds:
        sleep_duration = min_interval_seconds - elapsed_time_since_last_call
        # print(f"Rate limit: sleeping for {sleep_duration:.2f} seconds...")
        time.sleep(sleep_duration)
    LAST_API_CALL_TIME = time.time()

def call_insee_api(endpoint_url: str, api_token: str, params: dict = None) -> dict | None:
    """
    Calls the INSEE API, handles rate limiting, errors, and JSON parsing.
    """
    ensure_api_rate_limit()
    headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}

    session = requests.Session()
    request = requests.Request('GET', endpoint_url, params=params, headers=headers)
    prepared_request = session.prepare_request(request)

    # print(f"INFO: Calling API. Prepared URL: {prepared_request.url}") # Can be verbose

    try:
        response = session.send(prepared_request, timeout=20)
        if response.status_code == 200:
            try: return response.json()
            except json.JSONDecodeError: print(f"Error: Failed to parse JSON from API: {prepared_request.url}. Response: {response.text[:200]}..."); return None
        elif response.status_code == 401: print(f"API Error 401: Unauthorized (URL: {prepared_request.url}). Check token."); return None
        elif response.status_code == 403: print(f"API Error 403: Forbidden (URL: {prepared_request.url}). Invalid rights/token."); return None
        elif response.status_code == 404: print(f"API Error 404: Not Found: {prepared_request.url}"); return None
        elif response.status_code == 429: print(f"API Error 429: Too Many Requests (URL: {prepared_request.url})."); return None
        elif response.status_code == 400: print(f"API Error 400: Bad Request (URL: {prepared_request.url}). Details: {response.text}"); return None
        else: print(f"API Error {response.status_code} (URL: {prepared_request.url}). Response: {response.text[:200]}"); return None
    except requests.exceptions.Timeout: print(f"API Error: Timeout (20s) for URL: {prepared_request.url}"); return None
    except requests.exceptions.RequestException as e: print(f"API Connection Error (URL: {prepared_request.url}): {e}"); return None

def _build_complete_address(adresse_json: dict | None) -> str:
    """Constructs a complete address string from an addressEtablissement object."""
    if not adresse_json or not isinstance(adresse_json, dict): return ""
    parts = [
        adresse_json.get("numeroVoieEtablissement"), adresse_json.get("indiceRepetitionEtablissement"),
        adresse_json.get("typeVoieEtablissement"), adresse_json.get("libelleVoieEtablissement"),
        adresse_json.get("complementAdresseEtablissement"), adresse_json.get("codePostalEtablissement"),
        adresse_json.get("libelleCommuneEtablissement"), adresse_json.get("libelleCedexEtablissement")
    ]
    return " ".join(filter(None, [str(p).strip() for p in parts if p and str(p).strip()])).strip()

def parse_unite_legale_data(ul_json: dict | None) -> dict:
    """Parses relevant fields from the 'uniteLegale' JSON object."""
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
    """Parses relevant fields from an 'etablissement' JSON object."""
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
    """Retrieves and parses data for a specific SIRET."""
    url = f"{INSEE_API_BASE_URL}/siret/{siret.strip()}"
    response_json = call_insee_api(url, api_token, params=None)
    if response_json and "etablissement" in response_json:
        etablissement_raw = response_json["etablissement"]
        ul_data_raw = etablissement_raw.get("uniteLegale", {})
        parsed_ul_data = parse_unite_legale_data(ul_data_raw)
        return parse_etablissement_data(etablissement_raw, parsed_ul_data)
    return None

def get_data_by_siren(siren: str, api_token: str) -> dict | None:
    """Retrieves and parses data for a specific SIREN, prioritizing siege."""
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
            # print(f"Info: Siege found for SIREN {siren}, SIRET: {siege_etablissement_raw.get('siret')}. Fetching its full details.") # Verbose
            siege_siret = siege_etablissement_raw.get('siret')
            siege_details = get_data_by_siret(siege_siret, api_token)
            if siege_details:
                final_data = parsed_ul_data.copy()
                final_data.update(siege_details)
                return final_data
            else:
                # print(f"Warning: Failed to fetch full details for siege SIRET {siege_siret}. Using partial data from SIREN call for siege.") # Verbose
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
                 parsed_data["INSEE_EstSiege"] = False
            return parsed_data
    return None

def search_data_by_name(normalized_name: str, api_token: str, champs: list = None) -> list[dict] | None:
    """
    Searches for establishments by name using the INSEE API.
    Returns all establishments found. Client-side filtering for active status
    will be handled by the caller.

    Args:
        normalized_name (str): The normalized company name to search for.
        api_token (str): The API token.
        champs (list, optional): Specific fields to retrieve. Defaults to None (API default).

    Returns:
        list[dict] | None: A list of parsed establishment data dicts from API,
                           or None if API call error, or empty list if no matches.
    """
    base_url = f"{INSEE_API_BASE_URL}/siret"
    name_escaped = escape_lucene_value(normalized_name)
    query_string = f'denominationUniteLegale:"{name_escaped}"' # Simplest working query

    api_params = {"q": query_string}
    if champs: # Only add champs if provided and not empty
        api_params["champs"] = ",".join(champs)

    response_json = call_insee_api(base_url, api_token, params=api_params)

    if response_json and "etablissements" in response_json:
        all_results_parsed = []
        for etab_raw in response_json["etablissements"]:
            parsed_etab_data = parse_etablissement_data(etab_raw)
            all_results_parsed.append(parsed_etab_data)
        return all_results_parsed
    elif response_json and response_json.get("header", {}).get("total", 0) == 0:
        return [] # No results found
    return None # Error in API call or unexpected response structure

def search_data_by_name_and_city(first_word_of_name: str, city: str, api_token: str, champs: list = None) -> list[dict] | None:
    """
    Searches for establishments by the first word of the name and city.

    Args:
        first_word_of_name (str): The first word of the normalized company name.
        city (str): The city name (will be uppercased for query).
        api_token (str): The API token.
        champs (list, optional): Specific fields to retrieve. Defaults to DEFAULT_INSEE_FIELDS.

    Returns:
        list[dict] | None: A list of parsed establishment data, or None on error, or empty list if no matches.
    """
    base_url = f"{INSEE_API_BASE_URL}/siret"
    name_escaped = escape_lucene_value(first_word_of_name)
    city_escaped = escape_lucene_value(city.upper()) # API often expects uppercase for city

    # Querying on first word of denominationUniteLegale and exact match on libelleCommuneEtablissement
    # This assumes libelleCommuneEtablissement is directly queryable with periode wrapper.
    query_string = f'periode(denominationUniteLegale:"{name_escaped}"*) AND periode(libelleCommuneEtablissement:"{city_escaped}")'
    # Using wildcard * for prefix search on the name's first word.
    # Note: The effectiveness of combining periode() with wildcards and multiple ANDs needs API validation.
    # A simpler alternative if issues arise: f'denominationUniteLegale:"{name_escaped}"* AND libelleCommuneEtablissement:"{city_escaped}"'
    # Or even query for name, then filter by city client-side if q syntax is too restrictive.

    print(f"INFO: Recherche secondaire par nom/ville. Critères: PremierMotNom='{name_escaped}', Ville='{city_escaped}'")
    # print(f"DEBUG: Query string pour nom/ville: {query_string}")

    champs_to_use = champs if champs else DEFAULT_INSEE_FIELDS # Use global default if not specified
    api_params = {"q": query_string}
    if champs_to_use:
        api_params["champs"] = ",".join(champs_to_use)

    response_json = call_insee_api(base_url, api_token, params=api_params)

    if response_json is None: return None # API call failed
    if response_json.get("header", {}).get("statut") != 200 and response_json.get("header", {}).get("message") : # Check for API error message
        print(f"ERREUR API (Recherche Nom/Ville): Statut {response_json.get('header', {}).get('statut')} - {response_json.get('header', {}).get('message')}", file=sys.stderr)
        # If it's a syntax error, it might be better to return None to indicate failure rather than empty list
        if response_json.get("header", {}).get("statut") == 400 : return None
        return []


    etablissements_json = response_json.get("etablissements")
    if not etablissements_json:
        print(f"INFO: Aucun établissement trouvé par nom/ville pour '{first_word_of_name}' à '{city}'.")
        return []

    parsed_results_list = []
    for etab_json in etablissements_json:
        # UL data is nested under each etablissement in search results
        etab_data = parse_etablissement_data(etab_json)
        parsed_results_list.append(etab_data)

    print(f"INFO: Recherche nom/ville pour '{first_word_of_name}' à '{city}' a retourné {len(parsed_results_list)} résultat(s) après parsing.")
    return parsed_results_list


def main():
    """Main execution flow: parse args, load data, process rows, save results."""
    parser = argparse.ArgumentParser(description="Enrich company data using INSEE SIRENE API.")
    parser.add_argument( "--input-file", "-i", required=True, help="Path to the input CSV file.")
    parser.add_argument( "--output-file", "-o", required=True, help="Path to save the enriched output CSV file.")
    parser.add_argument( "--api-token", "-t", required=True, help="API token for INSEE SIRENE API.")
    parser.add_argument( "--multiple-matches-file", "-m", required=True, help="Path to save CSV file for multiple matches found via name search.")
    args = parser.parse_args()

    if args.output_file:
        base_name, ext = os.path.splitext(args.output_file)
        inactive_matches_filename = f"{base_name}_inactive_matches{ext}"
    else:
        inactive_matches_filename = "inactive_matches_default.csv"

    masked_token = f"{'*' * (len(args.api_token) - 4)}{args.api_token[-4:]}" if len(args.api_token) > 4 else "***"
    print("--- Configuration ---"); print(f"Input File: {args.input_file}"); print(f"Output File: {args.output_file}"); print(f"API Token: {masked_token}"); print(f"Multiple Matches File: {args.multiple_matches_file}"); print(f"Inactive Matches File: {inactive_matches_filename}"); print("---------------------\n")

    col_input_siret = "Siret"; col_input_siren = "siren"; col_input_nom_normalise = "nom_entreprise_normalise"
    col_address_city = "City" # Assuming this is the source column name for city

    try: df = pd.read_csv(args.input_file, dtype=str, keep_default_na=False, na_filter=False)
    except FileNotFoundError: print(f"Erreur: Le fichier d'entrée '{args.input_file}' n'a pas été trouvé."); sys.exit(1)
    except Exception as e: print(f"Erreur lors de la lecture du fichier d'entrée '{args.input_file}': {e}"); sys.exit(1)
    print(f"Loaded {len(df)} rows from {args.input_file}")

    for col_name in NEW_INSEE_COLUMNS_DEFINITION.keys(): df[col_name] = pd.NA

    multiple_matches_accumulator = []
    inactive_matches_accumulator = [] # Initialize accumulator for inactive matches

    print("Starting data enrichment process...")
    for index, row in df.iterrows():
        siret_val = str(row.get(col_input_siret, '')).strip()
        siren_val = str(row.get(col_input_siren, '')).strip()
        nom_val = str(row.get(col_input_nom_normalise, '')).strip()
        city_val = str(row.get(col_address_city, '')).strip() # Get city for secondary search

        processed_data_for_row = None; status_msg = pd.NA; attempt_secondary_search = False

        if not siret_val and not siren_val and not nom_val: status_msg = "Aucun critère de recherche"
        else:
            if siret_val and len(siret_val) == 14 and siret_val.isdigit():
                processed_data_for_row = get_data_by_siret(siret_val, args.api_token)
                if processed_data_for_row:
                    # Check activity for SIRET result
                    ul_status = processed_data_for_row.get("INSEE_StatutAdministratifUL", "")
                    etab_status = processed_data_for_row.get("INSEE_EtatAdministratifEtablissement", "")
                    if str(ul_status) == 'A' and str(etab_status) == 'A':
                        status_msg = "OK - SIRET (Actif)"
                    else:
                        status_msg = f"INSEE: SIRET trouvé inactif (UL:{ul_status}, Etab:{etab_status})"
                        # Add to inactive accumulator, do not populate main DF with this data
                        inactive_data = row.to_dict()
                        for k, v in processed_data_for_row.items(): inactive_data[f"INSEE_Candidat_{k}"] = v
                        inactive_matches_accumulator.append(inactive_data)
                        processed_data_for_row = None # Clear it so it's not written to main DF
                else:
                    status_msg = "INSEE: SIRET non trouvé/Erreur"

            if not processed_data_for_row and siren_val and len(siren_val) == 9 and siren_val.isdigit():
                processed_data_for_row = get_data_by_siren(siren_val, args.api_token)
                if processed_data_for_row:
                    ul_status = processed_data_for_row.get("INSEE_StatutAdministratifUL", "")
                    etab_status = processed_data_for_row.get("INSEE_EtatAdministratifEtablissement", "")
                    if str(ul_status) == 'A' and str(etab_status) == 'A':
                        status_msg = "OK - SIREN (Actif)"
                    else:
                        status_msg = f"INSEE: SIREN trouvé inactif (UL:{ul_status}, Etab:{etab_status})"
                        inactive_data = row.to_dict()
                        for k, v in processed_data_for_row.items(): inactive_data[f"INSEE_Candidat_{k}"] = v
                        inactive_matches_accumulator.append(inactive_data)
                        processed_data_for_row = None
                else:
                    status_msg = "INSEE: SIREN non trouvé/Erreur"

            if not processed_data_for_row and nom_val: # Primary Name Search
                print(f"Row {index+1}: Querying by Name '{nom_val}'")
                search_results = search_data_by_name(nom_val, args.api_token)
                if search_results is not None:
                    if len(search_results) == 0:
                        status_msg = "INSEE: Non trouvé par nom (1)" # Mark for secondary search
                        attempt_secondary_search = True
                    elif len(search_results) == 1:
                        candidate = search_results[0]
                        ul_status = candidate.get("INSEE_StatutAdministratifUL", "")
                        etab_status = candidate.get("INSEE_EtatAdministratifEtablissement", "")
                        if str(ul_status) == 'A' and str(etab_status) == 'A':
                            processed_data_for_row = candidate
                            status_msg = "OK - Nom (1 Résultat Actif)"
                        else:
                            status_msg = f"INSEE: Nom (1 Résultat Inactif UL:{ul_status}, Etab:{etab_status})"
                            inactive_data = row.to_dict()
                            for k, v in candidate.items(): inactive_data[f"INSEE_Candidat_{k}"] = v
                            inactive_matches_accumulator.append(inactive_data)
                    else: # Multiple results from primary name search
                        status_msg = f"INSEE: Plusieurs par nom ({len(search_results)}) - Dispatching..."
                        active_candidates_for_multiple = []
                        for candidate in search_results:
                            ul_status = candidate.get("INSEE_StatutAdministratifUL", "")
                            etab_status = candidate.get("INSEE_EtatAdministratifEtablissement", "")
                            if str(ul_status) == 'A' and str(etab_status) == 'A':
                                active_candidates_for_multiple.append(candidate)
                            else:
                                inactive_data = row.to_dict()
                                for k,v in candidate.items(): inactive_data[f"INSEE_Candidat_{k}"] = v
                                inactive_matches_accumulator.append(inactive_data)

                        if len(active_candidates_for_multiple) == 1:
                            processed_data_for_row = active_candidates_for_multiple[0]
                            status_msg = "OK - Nom (1 Actif sur Plusieurs)"
                        elif len(active_candidates_for_multiple) > 1:
                             status_msg = f"INSEE: Plusieurs Actifs par nom ({len(active_candidates_for_multiple)})"
                             multiple_matches_accumulator.append({'original_row_index': index,'original_data': row.to_dict(),'api_candidates': active_candidates_for_multiple})
                        else: # No active candidates among multiple results
                            status_msg = "INSEE: Plusieurs par nom (Tous Inactifs)"
                            # No need to attempt_secondary_search if all were inactive but found
                else:
                    status_msg = "INSEE: Erreur recherche Nom (1)"
                    attempt_secondary_search = True # Also attempt secondary if primary name search had API error

            # Secondary Name/City Search
            if attempt_secondary_search and nom_val and city_val:
                print(f"Row {index+1}: Attempting Secondary Search for '{nom_val.split(' ')[0]}' in '{city_val}'")
                first_word = nom_val.split(" ")[0]
                secondary_search_results = search_data_by_name_and_city(first_word, city_val, args.api_token)
                if secondary_search_results is not None:
                    if len(secondary_search_results) == 0:
                        status_msg = "INSEE: Non trouvé par Nom partiel/Ville"
                    elif len(secondary_search_results) == 1:
                        candidate = secondary_search_results[0]
                        ul_status = candidate.get("INSEE_StatutAdministratifUL", "")
                        etab_status = candidate.get("INSEE_EtatAdministratifEtablissement", "")
                        if str(ul_status) == 'A' and str(etab_status) == 'A':
                            processed_data_for_row = candidate
                            status_msg = "OK - Nom partiel/Ville (1 Résultat Actif)"
                        else:
                            status_msg = f"INSEE: Nom partiel/Ville (1 Résultat Inactif UL:{ul_status}, Etab:{etab_status})"
                            inactive_data = row.to_dict()
                            for k,v in candidate.items(): inactive_data[f"INSEE_Candidat_{k}"] = v
                            inactive_matches_accumulator.append(inactive_data)
                    else: # Multiple results from secondary search
                        status_msg = f"INSEE: Plusieurs par Nom partiel/Ville ({len(secondary_search_results)}) - Dispatching..."
                        active_candidates_for_multiple = []
                        for candidate in secondary_search_results:
                            ul_status = candidate.get("INSEE_StatutAdministratifUL", "")
                            etab_status = candidate.get("INSEE_EtatAdministratifEtablissement", "")
                            if str(ul_status) == 'A' and str(etab_status) == 'A':
                                active_candidates_for_multiple.append(candidate)
                            else:
                                inactive_data = row.to_dict()
                                for k,v in candidate.items(): inactive_data[f"INSEE_Candidat_{k}"] = v
                                inactive_matches_accumulator.append(inactive_data)

                        if len(active_candidates_for_multiple) == 1:
                            processed_data_for_row = active_candidates_for_multiple[0]
                            status_msg = "OK - Nom partiel/Ville (1 Actif sur Plusieurs)"
                        elif len(active_candidates_for_multiple) > 1:
                            status_msg = f"INSEE: Plusieurs Actifs par Nom partiel/Ville ({len(active_candidates_for_multiple)})"
                            multiple_matches_accumulator.append({'original_row_index': index,'original_data': row.to_dict(),'api_candidates': active_candidates_for_multiple})
                        else:
                             status_msg = "INSEE: Plusieurs par Nom partiel/Ville (Tous Inactifs)"
                else:
                    status_msg = "INSEE: Erreur recherche Nom partiel/Ville"

            if pd.isna(status_msg) and processed_data_for_row is None and (siret_val or siren_val or nom_val) :
                status_msg = "Critères fournis invalides ou API inaccessible"

        if processed_data_for_row: # Only active, single matches populate the main df
            for key, value in processed_data_for_row.items():
                if key in df.columns: df.loc[index, key] = value
        df.loc[index, "Statut_API_INSEE"] = status_msg
        if (index + 1) % 1 == 0 or (index + 1) == len(df):
            print(f"Processed {index + 1}/{len(df)} rows. Status: {status_msg}")

    print("\nEnrichment process completed.")
    try: df.to_csv(args.output_file, index=False, encoding='utf-8'); print(f"Enriched data saved to '{args.output_file}'")
    except Exception as e: print(f"Erreur lors de la sauvegarde du fichier de sortie principal: {e}")

    if multiple_matches_accumulator:
        print(f"\nFound {len(multiple_matches_accumulator)} rows with multiple ACTIVE matches. Preparing '{args.multiple_matches_file}'...")
        multiple_matches_df_rows = []
        for item in multiple_matches_accumulator:
            original_row_data = item['original_data']
            for candidate_data in item['api_candidates']:
                new_row = original_row_data.copy()
                new_row['original_row_index_in_input'] = item['original_row_index']
                for key, value in candidate_data.items(): new_row[f"INSEE_Candidat_{key}"] = value # Prefix for clarity
                multiple_matches_df_rows.append(new_row)
        if multiple_matches_df_rows:
            multiple_df = pd.DataFrame(multiple_matches_df_rows)
            try: multiple_df.to_csv(args.multiple_matches_file, index=False, encoding='utf-8'); print(f"Multiple matches data saved to '{args.multiple_matches_file}'")
            except Exception as e: print(f"Erreur lors de la sauvegarde du fichier des correspondances multiples (actives): {e}")
    else: print("No multiple (active) matches found to save.")

    if inactive_matches_accumulator:
        print(f"\nFound {len(inactive_matches_accumulator)} INACTIVE matches/candidates. Preparing '{inactive_matches_filename}'...")
        inactive_df = pd.DataFrame(inactive_matches_accumulator)
        try: inactive_df.to_csv(inactive_matches_filename, index=False, encoding='utf-8'); print(f"Inactive matches data saved to '{inactive_matches_filename}'")
        except Exception as e: print(f"Erreur lors de la sauvegarde du fichier des correspondances multiples (inactives): {e}")
    else: print("No inactive matches found to save.")
    print("\nScript finished.")

if __name__ == "__main__":
    main()
```
