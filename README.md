# EU VAT Number Validator (CSV Processor)

This script allows you to validate multiple European Union (EU) VAT (Value Added Tax) numbers from a CSV file using the official VIES (VAT Information Exchange System) API. It reads VAT numbers from a specified column in your input CSV, validates each one, and then writes the original data along with the validation results to a new output CSV file.

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

Run the script from your command line, providing the path to your input CSV file, the desired path for the output CSV file, and optionally, the name of the column in your input CSV that contains the VAT numbers.

### Syntax

```bash
python vat_validator.py <input_file.csv> <output_file.csv> [--vat_column "Column Name"]
```

### Arguments

-   `input_file.csv`: Path to the CSV file containing the VAT numbers to validate.
-   `output_file.csv`: Path where the script will save the CSV file with the validation results.
-   `--vat_column "Column Name"` (optional): The name of the column in your input CSV that holds the VAT numbers (e.g., "VAT No.", "Tax ID"). If not specified, it defaults to "VAT Registration No.". Make sure to use quotes if the column name contains spaces.

### Example Command

```bash
python vat_validator.py companies_to_check.csv validation_results.csv --vat_column "Tax ID"
```

If your VAT column is named "VAT Registration No.":
```bash
python vat_validator.py input.csv output.csv
```

## Input CSV File Example

Your input CSV file should contain a column with the VAT numbers (including the two-letter country prefix). For example, if your VAT numbers are in a column named "VAT Registration No.":

**`input.csv`:**
```csv
Company Name,VAT Registration No.,Other Data
"Tech Corp","FR27839029359","Some info"
"Euro Traders","DE123456789","More details"
"Invalid Ltd","GB123456789","Old UK VAT"
"Malformed VAT Inc.","FR 123 456","Data"
"No VAT Corp","","Empty VAT field"
```

## Output CSV File Example

The output CSV file will contain all the columns from your input file, plus additional columns prefixed with `vies_` containing the validation results from the VIES API.

**`output.csv` (example based on input above):**
```csv
Company Name,VAT Registration No.,Other Data,vies_country_code,vies_vat_number,vies_request_date,vies_valid,vies_name,vies_address,vies_error
"Tech Corp","FR27839029359","Some info",FR,27839029359,YYYY-MM-DD,True,"SOCIETE XXXX","1 RUE YYYY...",
"Euro Traders","DE123456789","More details",DE,123456789,YYYY-MM-DD,False,"","",""
"Invalid Ltd","GB123456789","Old UK VAT",GB,123456789,YYYY-MM-DD,False,"","",""
"Malformed VAT Inc.","FR 123 456","Data",,,,,,,Invalid VAT format: FR 123 456
"No VAT Corp","","Empty VAT field",,,,,,,Empty VAT number in source column
```
*(Note: `YYYY-MM-DD`, names, and addresses will vary based on actual VIES data and request time. `vies_valid` is a boolean. `vies_error` will contain API error messages or parsing issues.)*

## How it Works

The script reads each row from your input CSV file. For each row, it extracts the VAT number from the specified column, parses the country code and the number itself, and then queries the European Commission's VIES SOAP service using the `zeep` library. The original data from each row is then combined with the validation results (validity, name, address, etc.) and written to a new row in the output CSV file. Errors during parsing or API communication are logged in the `vies_error` column.

## Disclaimer

This script relies on the VIES service provided by the European Commission. The availability and accuracy of the data depend on this service and the databases of the EU Member States.
