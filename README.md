# EU VAT Number Validator

This script allows you to validate European Union (EU) VAT (Value Added Tax) numbers using the official VIES (VAT Information Exchange System) API.

## Prerequisites

- Python 3.x
- The `zeep` library

## Installation

1.  Clone this repository (or download the `vat_validator.py` script).
2.  Install the required Python library:
    ```bash
    pip install -r requirements.txt
    ```
    (If you only downloaded the script, you can install `zeep` directly: `pip install zeep`)

## Usage

Run the script from your command line, providing the two-letter country code and the VAT number (without the country code) as arguments.

### Syntax

```bash
python vat_validator.py <country_code> <vat_number>
```

### Examples

**Valid VAT Number:**

```bash
python vat_validator.py FR 27839029359
```

Example Output:
```
VAT Number: FR27839029359
Request Date: YYYY-MM-DD
Valid: True
Name: SOCIETE XXXX
Address: 1 RUE YYYY
75000 PARIS
```
*(Note: The actual name, address, and request date will vary.)*

**Invalid VAT Number:**

```bash
python vat_validator.py DE 123456789
```

Example Output:
```
VAT Number: DE123456789
Request Date: YYYY-MM-DD
Valid: False
```

**Error Handling (e.g., invalid country code):**

```bash
python vat_validator.py XX 123456789
```

Example Output:
```
Error validating VAT number XX123456789:
SOAP Fault: INVALID_INPUT
```

## How it Works

The script uses the `zeep` library to communicate with the European Commission's VIES SOAP service. It sends a `checkVat` request with the provided country code and VAT number and then displays the validation result, including whether the number is valid, and if available, the name and address associated with the VAT number.

## Disclaimer

This script relies on the VIES service provided by the European Commission. The availability and accuracy of the data depend on this service and the databases of the EU Member States.
