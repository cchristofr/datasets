import argparse
import zeep
from zeep.exceptions import Fault
import csv # Added import

# WSDL URL for the VIES VAT checking service
VIES_WSDL_URL = 'http://ec.europa.eu/taxation_customs/vies/services/checkVatService.wsdl'

def check_vat_number(country_code: str, vat_number: str) -> dict:
    """
    Checks the validity of a VAT number using the VIES SOAP service.

    Args:
        country_code: The two-letter country code (e.g., "FR", "DE").
        vat_number: The VAT number (without the country code).

    Returns:
        A dictionary containing the validation result:
        {
            'country_code': str,
            'vat_number': str,
            'request_date': str, # YYYY-MM-DD
            'valid': bool,
            'name': str or None,
            'address': str or None,
            'error': str or None # Error message if any
        }
    """
    try:
        client = zeep.Client(wsdl=VIES_WSDL_URL)
        # Ensure country_code is uppercase as per VIES documentation
        country_code = country_code.upper()
        response = client.service.checkVat(countryCode=country_code, vatNumber=vat_number)

        return {
            'country_code': response.countryCode,
            'vat_number': response.vatNumber,
            'request_date': response.requestDate.strftime('%Y-%m-%d'),
            'valid': response.valid,
            'name': response.name if hasattr(response, 'name') and response.name else None,
            'address': response.address if hasattr(response, 'address') and response.address else None,
            'error': None
        }
    except Fault as fault:
        return {
            'country_code': country_code,
            'vat_number': vat_number,
            'request_date': None,
            'valid': False,
            'name': None,
            'address': None,
            'error': f"SOAP Fault: {fault.message}"
        }
    except Exception as e:
        return {
            'country_code': country_code,
            'vat_number': vat_number,
            'request_date': None,
            'valid': False,
            'name': None,
            'address': None,
            'error': f"An unexpected error occurred: {str(e)}"
        }

def parse_vat_string(full_vat_string: str) -> tuple:
    """
    Parses a full VAT string into country code and VAT number part.
    Example: "FR27839029359" -> ("FR", "27839029359")
    """
    if not full_vat_string or len(full_vat_string) < 3:
        return None, None

    country_code = full_vat_string[:2]
    vat_number_part = full_vat_string[2:]

    if not country_code.isalpha() or not len(country_code) == 2:
        return None, None

    return country_code.upper(), vat_number_part

def process_csv(input_filepath: str, output_filepath: str, vat_column_name: str):
    """
    Processes VAT numbers from an input CSV file and writes results to an output CSV file.
    """
    print(f"Starting CSV processing. Input: {input_filepath}, Output: {output_filepath}, VAT Column: {vat_column_name}")

    try:
        with open(input_filepath, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            if not reader.fieldnames:
                print(f"Error: Input CSV file '{input_filepath}' is empty or has no header.")
                return

            fieldnames = reader.fieldnames
            output_fieldnames = fieldnames + ['vies_country_code', 'vies_vat_number', 'vies_request_date', 'vies_valid', 'vies_name', 'vies_address', 'vies_error']

            try:
                with open(output_filepath, mode='w', newline='', encoding='utf-8') as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
                    writer.writeheader()

                    for row in reader:
                        output_row = row.copy()
                        vies_data = {key: '' for key in output_fieldnames if key.startswith('vies_')} # Initialize with empty strings

                        full_vat_str = row.get(vat_column_name, "").strip()

                        if not full_vat_str:
                            vies_data['vies_error'] = "Empty VAT number in source column"
                        else:
                            country_code, vat_number_part = parse_vat_string(full_vat_str)
                            if country_code and vat_number_part:
                                api_response = check_vat_number(country_code, vat_number_part)
                                vies_data['vies_country_code'] = api_response.get('country_code', country_code) # Use parsed if API fails early
                                vies_data['vies_vat_number'] = api_response.get('vat_number', vat_number_part) # Use parsed if API fails early
                                vies_data['vies_request_date'] = api_response.get('request_date', '')
                                vies_data['vies_valid'] = api_response.get('valid', False)
                                vies_data['vies_name'] = api_response.get('name', '')
                                vies_data['vies_address'] = api_response.get('address', '')
                                vies_data['vies_error'] = api_response.get('error', '')
                            else:
                                vies_data['vies_error'] = f"Invalid VAT format: {full_vat_str}"

                        output_row.update(vies_data)
                        writer.writerow(output_row)

                print(f"Processing complete. Output written to {output_filepath}")

            except IOError as e:
                print(f"Error writing to output file {output_filepath}: {e}")

    except FileNotFoundError:
        print(f"Error: Input CSV file '{input_filepath}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred during CSV processing: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate EU VAT numbers from a CSV file using the VIES service.")
    parser.add_argument("input_file", help="Path to the input CSV file.")
    parser.add_argument("output_file", help="Path to the output CSV file.")
    parser.add_argument("--vat_column", default="VAT Registration No.", help="Name of the column in the CSV containing the VAT number (default: 'VAT Registration No.').")

    args = parser.parse_args()

    process_csv(args.input_file, args.output_file, args.vat_column)
