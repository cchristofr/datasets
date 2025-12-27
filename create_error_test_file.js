const XLSX = require('xlsx');

const data = [
    // Supplier Scenario for error testing
    {
        'BUKRS': 'S-ERR', 'LIFNR': 'S-ERR-1', 'NAME1': 'API Error Test Supplier',
        // SIRET to trigger 404
        'STCD1': '11111111111111',
        // SIRET to trigger 503
        'Primary Business Name': 'API ERROR TEST SUPPLIER',
        'Registration Number 1 Type Desc': 'SIRET (FR)',
        'Registration Number 1': '22222222222222',
        'Correction': '', 'Commentaire': ''
    },
    // Client Scenario for network error
    {
        'BUKRS': 'C-ERR', 'KUNNR': 'C-ERR-2', 'LOCAL_NAME1': 'API Network Error Client',
        // SIRET to trigger network error
        'TAX_NB1': '33333333333333',
        // Another SIRET to trigger network error
        'Primary Business Name': 'API NETWORK ERROR CLIENT',
        'Registration Number 1 Type Desc': 'SIRET (FR)',
        'Registration Number 1': '44444444444444',
        'Correction': '', 'Commentaire': ''
    }
];

const worksheet = XLSX.utils.json_to_sheet(data);
const workbook = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(workbook, worksheet, 'ErrorTest');
XLSX.writeFile(workbook, 'dummy_sirene_error_test.xlsx');

console.log('dummy_sirene_error_test.xlsx created successfully.');
