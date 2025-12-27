const XLSX = require('xlsx');

const data = [
    // Supplier Scenario
    {
        'BUKRS': 'S001', 'KTOKK': 'SUPP', 'LIFNR': 'S-98765', 'ERDAT': '2023-02-01', 'LAST_EVENT': '2024-04-10',
        'NAME1': 'Supplier Fallback Test', 'NAME2': 'SFT',
        'LOCAL_STR_SUPPL1': '', 'LOCAL_STR_SUPPL2': '', 'LOCAL_STR_SUPPL3': '',
        'LOCAL_STREET': '456 Supplier Ave', 'LOCAL_CITY1': 'Supplierville', 'LOCAL_POST_CODE1': '54321', 'LAND1': 'FR',
        'STCD1': '98765432109876', 'STCD2': '', // SIREN is empty
        'FOUR_TAX': 'FR07987654321', // Valid French VAT
        'FLAG SIREN': '', 'FLAG SIRET': 'ID',
        'Primary Business Name': 'SUPPLIER FALLBACK TEST',
        'Primary Address Street Line 1': '456 SUPPLIER AVE',
        'Primary Address Locality Name': 'SUPPLIERVILLE', 'Organization Primary Address Postal Code': '54321',
        'Primary Address ISO Alpha 2 Char Country Code': 'FR',
        'Registration Number 1 Type Desc': 'SIREN (FR)', 'Registration Number 1': '987654321', // Correct SIREN
        'TVA Code': 'FR07987654321',
        'Correction': '', 'Commentaire': ''
    },
    // Client Scenario
    {
        'BUKRS': 'C002', 'KTOKD': 'CLNT', 'KUNNR': 'C-54321', 'ERDAT': '2023-03-15', 'LAST_BUDAT': '2024-06-25',
        'LOCAL_NAME1': 'Client Fallback Test', 'LOCAL_NAME2': 'CFT',
        'LOCAL_STR_SUPPL1': '', 'LOCAL_STR_SUPPL2': '', 'LOCAL_STR_SUPPL3': '',
        'LOCAL_STREET': '789 Client Blvd', 'LOCAL_CITY1': 'Clientville', 'LOCAL_POST_CODE1': '12345', 'LOCAL_COUNTRY': 'FR',
        'TAX_NB1': '54321098765432', 'TAX_NB2': '', // SIREN is empty
        'VAT': 'FR12543210987', // Valid French VAT
        'FLAG SIREN': '', 'FLAG SIRET': 'ID',
        'Primary Business Name': 'CLIENT FALLBACK TEST',
        'Primary Address Street Line 1': '789 CLIENT BLVD',
        'Primary Address Locality Name': 'CLIENTVILLE', 'Organization Primary Address Postal Code': '12345',
        'Primary Address ISO Alpha 2 Char Country Code': 'FR',
        'Registration Number 1 Type Desc': 'SIREN (FR)', 'Registration Number 1': '543210987', // Correct SIREN
        'TVA Code': 'FR12543210987',
        'Correction': '', 'Commentaire': ''
    }
];

const worksheet = XLSX.utils.json_to_sheet(data);
const workbook = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(workbook, worksheet, 'FallbackTest');
XLSX.writeFile(workbook, 'dummy_siren_fallback_test.xlsx');

console.log('dummy_siren_fallback_test.xlsx created successfully.');
