import argparse
import zeep
from zeep.exceptions import Fault

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate an EU VAT number using the VIES service.")
    parser.add_argument("country_code", type=str, help="Two-letter EU country code (e.g., FR, DE).")
    parser.add_argument("vat_number", type=str, help="VAT number (without the country code).")

    args = parser.parse_args()

    result = check_vat_number(args.country_code, args.vat_number)

    if result['error']:
        print(f"Error validating VAT number {args.country_code}{args.vat_number}:")
        print(result['error'])
    else:
        print(f"VAT Number: {result['country_code']}{result['vat_number']}")
        print(f"Request Date: {result['request_date']}")
        print(f"Valid: {result['valid']}")
        if result['name']:
            print(f"Name: {result['name']}")
        if result['address']:
            print(f"Address: {result['address']}")
