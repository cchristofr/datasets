const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');

// Mock data simulating the INSEE API responses
const MOCK_API_RESPONSES = {
    '75381355100028': { // Closed establishment
        etablissement: {
            periodesEtablissement: [{ dateFin: null, etatAdministratifEtablissement: 'F' }]
        }
    },
    '88035659100037': { // Active establishment
        etablissement: {
            periodesEtablissement: [{ dateFin: null, etatAdministratifEtablissement: 'A' }]
        }
    }
};

async function runTest(page, htmlFile, testName, companyName, rowIndex) {
    console.log(`--- Starting test: ${testName} ---`);

    // Reset page content and listeners for each test run
    await page.goto('about:blank');

    // Intercept network requests to mock the API call
    await page.route('**/api-sirene/3.11/siret/*', (route, request) => {
        const url = request.url();
        const siret = url.split('/').pop();
        console.log(`Intercepted API call for SIRET: ${siret}`);
        if (MOCK_API_RESPONSES[siret]) {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_API_RESPONSES[siret])
            });
        } else {
            route.fulfill({ status: 404 });
        }
    });

    const filePath = path.resolve(__dirname, htmlFile);
    await page.goto(`file://${filePath}`);

    let alertTriggered = false;
    // Set up a fresh dialog listener for this specific test run
    const dialogHandler = async dialog => {
        console.log(`Alert message for ${testName}: ${dialog.message()}`);
        assert(dialog.message().includes('est un établissement actif'), 'Alert message is incorrect.');
        alertTriggered = true;
        await dialog.dismiss();
        page.removeListener('dialog', dialogHandler); // Clean up listener
    };
    page.on('dialog', dialogHandler);

    const fileInput = await page.$('#file-input');
    const dummyFilePath = path.resolve(__dirname, 'dummy_sirene_api_test.xlsx');
    await fileInput.setInputFiles(dummyFilePath);

    await page.waitForSelector('#results .card-panel');

    const companyCard = await page.locator('.company-card', { hasText: companyName });
    const sireneButton = companyCard.locator('button', { hasText: 'Vérifier SIRENE' });
    await sireneButton.click();

    const originalStatusSelector = `#siret-original-status-${rowIndex}`;
    const correctedStatusSelector = `#siret-corrected-status-${rowIndex}`;

    await page.waitForSelector(`${originalStatusSelector}:has-text("Etb Fermé")`, { timeout: 5000 });
    console.log('Original SIRET status badge verified.');

    await page.waitForSelector(`${correctedStatusSelector}:has-text("Actif")`, { timeout: 5000 });
    console.log('Corrected SIRET status badge verified.');

    assert(alertTriggered, 'The alert for an active corrected SIRET was not triggered.');
    console.log('Alert verification successful.');

    const screenshotPath = `${testName}_api_screenshot.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved to ${screenshotPath}`);

    // Unroute to avoid conflicts with the next test
    await page.unroute('**/api-sirene/3.11/siret/*');
}

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    try {
        await runTest(page, 'index.html', 'SupplierApiTest', 'API Test Supplier', 0);
        await runTest(page, 'index_clients.html', 'ClientApiTest', 'API Test Client', 1);
    } catch (error) {
        console.error('A test failed:', error.message);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
