const XLSX = require('xlsx');

const data = [
    // Supplier Scenario with real SIRETs for API testing
    {
        'BUKRS': 'S001', 'KTOKK': 'SUPP', 'LIFNR': 'S-API-1',
        'NAME1': 'API Test Supplier',
        // Inactive SIRET (Original)
        'STCD1': '75381355100028',
        'STCD2': '753813551',
        // Active SIRET (Corrected)
        'Primary Business Name': 'API TEST SUPPLIER',
        'Registration Number 1 Type Desc': 'SIRET (FR)',
        'Registration Number 1': '88035659100037', // Active SIRET of "Gie LexImpact"
        'Correction': '', 'Commentaire': ''
    },
    // Client Scenario with real SIRETs for API testing
    {
        'BUKRS': 'C002', 'KTOKD': 'CLNT', 'KUNNR': 'C-API-2',
        'LOCAL_NAME1': 'API Test Client',
        // Inactive SIRET (Original)
        'TAX_NB1': '75381355100028',
        'TAX_NB2': '753813551',
        // Active SIRET (Corrected)
        'Primary Business Name': 'API TEST CLIENT',
        'Registration Number 1 Type Desc': 'SIRET (FR)',
        'Registration Number 1': '88035659100037',
        'Correction': '', 'Commentaire': ''
    }
];

const worksheet = XLSX.utils.json_to_sheet(data);
const workbook = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(workbook, worksheet, 'ApiTest');
XLSX.writeFile(workbook, 'dummy_sirene_api_test.xlsx');

console.log('dummy_sirene_api_test.xlsx created successfully.');
