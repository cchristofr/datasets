const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');

async function runTest(page, htmlFile, testName, companyName) {
    console.log(`--- Starting test: ${testName} ---`);

    const filePath = path.resolve(__dirname, htmlFile);
    await page.goto(`file://${filePath}`);

    // Upload the dummy file
    const fileInput = await page.$('#file-input');
    const dummyFilePath = path.resolve(__dirname, 'dummy_siren_fallback_test.xlsx');
    await fileInput.setInputFiles(dummyFilePath);

    // Wait for the comparison results to appear
    await page.waitForSelector('#results .card-panel');

    // Find the specific company card and check the SIREN row color
    const companyCard = await page.locator('.company-card', { hasText: companyName });
    const sirenRow = companyCard.locator('tr', { hasText: 'SIREN' });
    const correctedCell = sirenRow.locator('td').last();

    const cellClass = await correctedCell.getAttribute('class');

    assert(cellClass.includes('green'), `Verification failed for ${testName}: SIREN field is not green. Found class: ${cellClass}`);
    console.log(`Verification successful for ${testName}: SIREN field is green.`);

    const screenshotPath = `${testName}_fallback_screenshot.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved to ${screenshotPath}`);
}


(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    try {
        await runTest(page, 'index.html', 'SupplierApp', 'Supplier Fallback Test');
        await runTest(page, 'index_clients.html', 'ClientApp', 'Client Fallback Test');
    } catch (error) {
        console.error('A test failed:', error.message);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
