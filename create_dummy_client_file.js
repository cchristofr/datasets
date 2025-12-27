const XLSX = require('xlsx');

const data = [
    {
        'BUKRS': 'C001',
        'KTOKD': 'DEBI',
        'KUNNR': '12345',
        'ERDAT': '2023-01-15',
        'LAST_BUDAT': '2024-05-20',
        'LOCAL_NAME1': 'Client Test Inc.',
        'LOCAL_NAME2': 'CTI',
        'LOCAL_STR_SUPPL1': 'Bat C',
        'LOCAL_STR_SUPPL2': 'Etage 2',
        'LOCAL_STR_SUPPL3': 'Porte 5',
        'LOCAL_STREET': '123 Rue de Test',
        'LOCAL_CITY1': 'Testville',
        'LOCAL_POST_CODE1': '75001',
        'LOCAL_COUNTRY': 'FR',
        'TAX_NB1': '12345678901234', // SIRET
        'TAX_NB2': '123456789',      // SIREN
        'VAT': 'FR123456789',
        'FLAG SIREN': 'ID',
        'FLAG SIRET': '',
        // Corrected Data
        'Primary Business Name': 'CLIENT TEST INC',
        'Primary Address Street Line 1': '123 RUE DE TEST',
        'Primary Address Street Line 2': '',
        'Primary Address Locality Name': 'TESTVILLE',
        'Organization Primary Address Postal Code': '75001',
        'Primary Address ISO Alpha 2 Char Country Code': 'FR',
        'Registration Number 1 Type Desc': 'SIREN (FR)',
        'Registration Number 1': '123456789',
        'Registration Number 2 Type Desc': 'SIRET (FR)',
        'Registration Number 2': '12345678901234',
        'TVA Code': 'FR123456789',
        'Correction': '',
        'Commentaire': ''
    }
];

const worksheet = XLSX.utils.json_to_sheet(data);
const workbook = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(workbook, worksheet, 'Clients');
XLSX.writeFile(workbook, 'dummy_clients.xlsx');

console.log('dummy_clients.xlsx created successfully.');
