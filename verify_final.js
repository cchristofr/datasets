const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');

// --- Mock Data ---
const MOCK_SUCCESS_API = {
    '75381355100028': { etablissement: { periodesEtablissement: [{ dateFin: null, etatAdministratifEtablissement: 'F' }] } },
    '88035659100037': { etablissement: { periodesEtablissement: [{ dateFin: null, etatAdministratifEtablissement: 'A' }] } }
};

// --- Test Runner ---
async function runTest(page, config) {
    console.log(`--- Starting test: ${config.testName} ---`);

    await page.goto('about:blank');
    await page.route('**/api-sirene/3.11/siret/*', config.mockHandler);

    let alertTriggered = false;
    const dialogHandler = async dialog => {
        if (config.expectAlert) {
            console.log(`Alert message for ${config.testName}: ${dialog.message()}`);
            assert(dialog.message().includes('est un établissement actif'), 'Alert message is incorrect.');
            alertTriggered = true;
        }
        await dialog.dismiss();
        page.removeListener('dialog', dialogHandler);
    };
    page.on('dialog', dialogHandler);

    await page.goto(`file://${path.resolve(__dirname, config.htmlFile)}`);
    const fileInput = await page.$('#file-input');
    await fileInput.setInputFiles(path.resolve(__dirname, config.testFile));

    await page.waitForSelector('#results .card-panel');
    const companyCard = await page.locator('.company-card', { hasText: config.companyName });
    const sireneButton = companyCard.locator('button', { hasText: 'Vérifier SIRENE' });
    await sireneButton.click();

    await page.waitForSelector(`${config.originalStatusSelector}:has-text("${config.expectedOriginalText}")`, { timeout: 5000 });
    console.log(`Original status verified: ${config.expectedOriginalText}`);

    await page.waitForSelector(`${config.correctedStatusSelector}:has-text("${config.expectedCorrectedText}")`, { timeout: 5000 });
    console.log(`Corrected status verified: ${config.expectedCorrectedText}`);

    if (config.expectAlert) {
        assert(alertTriggered, 'The expected alert was not triggered.');
        console.log('Alert verification successful.');
    }

    const screenshotPath = `${config.testName}_screenshot.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved to ${screenshotPath}`);

    await page.unroute('**/api-sirene/3.11/siret/*');
}

// --- Main Execution ---
(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    try {
        // Test Suite 1: Success cases
        await runTest(page, {
            testName: 'Supplier_Success', htmlFile: 'index.html', testFile: 'dummy_sirene_api_test.xlsx',
            companyName: 'API Test Supplier', rowIndex: 0, expectAlert: true,
            originalStatusSelector: '#siret-original-status-0', expectedOriginalText: 'Etb Fermé',
            correctedStatusSelector: '#siret-corrected-status-0', expectedCorrectedText: 'Actif',
            mockHandler: (route, request) => {
                const siret = request.url().split('/').pop();
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SUCCESS_API[siret]) });
            }
        });
        await runTest(page, {
            testName: 'Client_Success', htmlFile: 'index_clients.html', testFile: 'dummy_sirene_api_test.xlsx',
            companyName: 'API Test Client', rowIndex: 1, expectAlert: true,
            originalStatusSelector: '#siret-original-status-1', expectedOriginalText: 'Etb Fermé',
            correctedStatusSelector: '#siret-corrected-status-1', expectedCorrectedText: 'Actif',
            mockHandler: (route, request) => {
                const siret = request.url().split('/').pop();
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SUCCESS_API[siret]) });
            }
        });

        // Test Suite 2: Error cases
        await runTest(page, {
            testName: 'Supplier_Errors', htmlFile: 'index.html', testFile: 'dummy_sirene_error_test.xlsx',
            companyName: 'API Error Test Supplier', rowIndex: 0, expectAlert: false,
            originalStatusSelector: '#siret-original-status-0', expectedOriginalText: 'SIRET non trouvé',
            correctedStatusSelector: '#siret-corrected-status-0', expectedCorrectedText: 'Erreur API (503)',
            mockHandler: (route, request) => {
                const siret = request.url().split('/').pop();
                if (siret === '11111111111111') route.fulfill({ status: 404 });
                else if (siret === '22222222222222') route.fulfill({ status: 503 });
                else route.continue();
            }
        });
        await runTest(page, {
            testName: 'Client_NetworkError', htmlFile: 'index_clients.html', testFile: 'dummy_sirene_error_test.xlsx',
            companyName: 'API Network Error Client', rowIndex: 1, expectAlert: false,
            originalStatusSelector: '#siret-original-status-1', expectedOriginalText: 'Erreur Réseau',
            correctedStatusSelector: '#siret-corrected-status-1', expectedCorrectedText: 'Erreur Réseau',
            mockHandler: (route) => route.abort()
        });

    } catch (error) {
        console.error('A test failed:', error.message);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
