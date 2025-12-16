const { chromium } = require('playwright');
const path = require('path');

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    const filePath = path.resolve(__dirname, 'index_clients.html');
    await page.goto(`file://${filePath}`);

    // Upload the dummy file
    const fileInput = await page.$('#file-input');
    const dummyFilePath = path.resolve(__dirname, 'dummy_clients.xlsx');
    await fileInput.setInputFiles(dummyFilePath);

    // Wait for the comparison results to appear
    await page.waitForSelector('#results .card-panel');

    // Verify the header content
    const headerText = await page.textContent('.company-card p');
    if (
        headerText.includes('Type de client: DEBI') &&
        headerText.includes('ID SAP: 12345') &&
        headerText.includes('Dernier événement: 2024-05-20')
    ) {
        console.log('Verification successful: Header contains correct client data.');
    } else {
        console.error('Verification failed: Header does not contain correct client data.');
        console.log('Found header text:', headerText);
    }

    // Take a screenshot
    const screenshotPath = 'client_verification_screenshot.png';
    await page.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved to ${screenshotPath}`);

    await browser.close();
})();
