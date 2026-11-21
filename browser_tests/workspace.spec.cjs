const { test, expect } = require('@playwright/test');

async function signIn(page, username = 'nurse', password = 'password123') {
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

async function addPatient(page, patient) {
  const form = page.locator('#patient-form');
  if (!(await form.isVisible())) await page.getByText('Add patient', { exact: true }).click();
  await form.getByLabel('Patient ID (synthetic)').fill(patient.id);
  await form.getByLabel('Name', { exact: true }).fill(patient.name);
  await form.getByLabel('Ward', { exact: true }).fill(patient.ward);
  await form.getByLabel('Bed', { exact: true }).fill(patient.bed);
  await form.getByRole('button', { name: 'Add Patient' }).click();
  await expect(page.getByText(`Patient ${patient.id} added.`)).toBeVisible();
  await expect(page.getByRole('rowheader', { name: patient.id })).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('sign-in errors and role navigation', async ({ page }) => {
  const nav = page.getByRole('navigation', { name: 'Workspace' });
  await signIn(page, 'nurse', 'incorrect');
  await expect(page.getByRole('alert')).toHaveText('Invalid username or password');
  await expect(page.getByLabel('Password', { exact: true })).toBeFocused();

  await signIn(page);
  await expect(nav.getByRole('button')).toHaveText(['Ward List', 'Record Observation']);
  await expect(nav.getByRole('button', { name: 'Ward List' })).toHaveAttribute('aria-current', 'page');
  await page.getByRole('button', { name: 'Sign Out' }).click();
  await expect(page.getByLabel('Username', { exact: true })).toBeFocused();

  await signIn(page, 'clinician');
  await expect(page.locator('#user-role')).toHaveText('Charge nurse');
  await nav.getByRole('button', { name: 'Escalations' }).click();
  await expect(page.getByRole('heading', { name: 'Open Escalations' })).toBeFocused();
  await expect(page.getByText('No open escalations.')).toBeVisible();
  await page.getByRole('button', { name: 'Sign Out' }).click();

  await signIn(page, 'admin');
  await expect(nav.getByRole('button')).toHaveText(['Administration']);
  await expect(page.getByRole('heading', { name: 'Administration' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ward List' })).toBeHidden();
});

test('revoked session returns to sign-in and clears the workspace', async ({ page, request }) => {
  await page.route('**/api/ward-list*', route => route.fulfill({ status: 503, json: {} }), { times: 1 });
  const login = page.waitForResponse(response => response.url().endsWith('/api/login') && response.ok());
  await signIn(page);
  const { access_token } = await (await login).json();
  await expect(page.getByRole('heading', { name: 'Ward List' })).toBeVisible();
  const retry = page.getByRole('button', { name: 'Retry patient list' });
  await expect(retry).toBeVisible();

  const logout = await request.post('/api/logout', { headers: { Authorization: `Bearer ${access_token}` } });
  expect(logout.status()).toBe(204);
  await retry.click();
  await expect(page.getByRole('alert')).toHaveText('Your session has ended. Please sign in again.');
  await expect(page.getByLabel('Username', { exact: true })).toBeFocused();
  await expect(page.locator('#ward-list')).toBeEmpty();
});

test('session expiry returns to sign-in without waiting for another request', async ({ page }) => {
  await page.clock.install();
  const login = page.waitForResponse(response => response.url().endsWith('/api/login') && response.ok());
  await signIn(page);
  const { expires_in } = await (await login).json();
  await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();
  await page.clock.fastForward(expires_in * 1000);
  await expect(page.getByRole('alert')).toHaveText('Your session has ended. Please sign in again.');
  await expect(page.getByLabel('Username', { exact: true })).toBeFocused();
});

test('creates and filters patients and reports a duplicate ID inline', async ({ page }) => {
  await signIn(page);
  await addPatient(page, { id: 'P-101', name: 'Synthetic One', ward: 'East', bed: '01' });
  await addPatient(page, { id: 'P-102', name: 'Synthetic Two', ward: 'West', bed: '02' });
  await page.getByLabel('Filter by ward').selectOption('West');
  await expect(page.getByRole('rowheader', { name: 'P-102' })).toBeVisible();
  await expect(page.getByRole('rowheader', { name: 'P-101' })).toHaveCount(0);

  const form = page.locator('#patient-form');
  const id = form.getByLabel('Patient ID (synthetic)');
  await id.fill('P-102');
  await form.getByLabel('Name', { exact: true }).fill('Duplicate ID');
  await form.getByLabel('Ward', { exact: true }).fill('West');
  await form.getByLabel('Bed', { exact: true }).fill('03');
  await form.getByRole('button', { name: 'Add Patient' }).click();
  await expect(id).toBeFocused();
  await expect(id).toHaveAccessibleDescription('Patient ID P-102 already exists.');
  await expect(form.getByLabel('Bed', { exact: true })).toHaveValue('03');
});

test('edit form handles missing update API and refreshes after a successful update response', async ({ page }) => {
  await signIn(page);
  await addPatient(page, { id: 'P-201', name: 'Synthetic Before', ward: 'East', bed: '04' });
  const edit = page.getByRole('button', { name: 'Edit patient P-201' });
  const form = page.locator('#patient-form');
  const name = form.getByLabel('Name', { exact: true });
  await edit.focus();
  await edit.press('Enter');
  await expect(name).toBeFocused();
  await expect(name).toHaveValue('Synthetic Before');
  await expect(form.getByLabel('Patient ID (synthetic)')).toHaveAttribute('readonly', '');
  await form.getByRole('button', { name: 'Cancel edit' }).click();
  await expect(edit).toBeFocused();
  await edit.click();
  await name.fill('Synthetic After');
  const save = form.getByRole('button', { name: 'Save Changes' });
  await page.route('**/api/patients/P-201', route => route.fulfill({ status: 404, json: {} }), { times: 1 });
  await save.click();
  await expect(page.getByRole('alert')).toContainText('Patient updates are unavailable');
  await expect(name).toHaveValue('Synthetic After');

  let updated;
  await page.route('**/api/patients/P-201', async route => {
    expect(route.request().method()).toBe('PATCH');
    expect(route.request().postDataJSON()).toEqual({ name: 'Synthetic After', ward: 'East', bed: '04' });
    updated = { patient_id: 'P-201', ...route.request().postDataJSON() };
    await route.fulfill({ json: updated });
  });
  for (const endpoint of ['patients', 'ward-list']) {
    await page.route(`**/api/${endpoint}`, async route => {
      const response = await route.fetch();
      const rows = await response.json();
      await route.fulfill({ response, json: rows.map(row => row.patient_id === 'P-201' ? { ...row, ...updated } : row) });
    });
  }
  await save.click();
  await expect(page.getByText('Patient P-201 updated.')).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Synthetic After' })).toBeVisible();
});

test('observation form works by keyboard on a narrow screen and focuses validation errors', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await signIn(page);
  await addPatient(page, { id: 'P-301', name: 'Synthetic Observation', ward: 'North', bed: '01' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(375);
  await page.getByRole('button', { name: 'Record observation for P-301' }).press('Enter');
  const patient = page.getByLabel('Patient', { exact: true });
  await expect(patient).toHaveValue('P-301');
  await expect(patient).toBeFocused();
  const save = page.getByRole('button', { name: 'Save & Score' });
  await save.press('Enter');
  const rate = page.getByLabel('Respiratory rate (breaths/min)');
  await expect(rate).toBeFocused();
  await expect(rate).toHaveAttribute('aria-invalid', 'true');
  await expect(rate).toHaveAccessibleDescription('This field is required.');

  await rate.fill('61');
  await save.press('Enter');
  await expect(rate).toHaveAccessibleDescription('Enter a value between 1 and 60.');
  await rate.fill('16');
  await page.getByLabel('SpO2 (%)').fill('98');
  await page.getByLabel('Supplemental oxygen?').selectOption('false');
  await page.getByLabel('Systolic BP (mmHg)').fill('120');
  await page.getByLabel('Pulse (beats/min)').fill('70');
  await page.getByLabel('Consciousness').selectOption('A');
  await page.getByLabel('Temperature (°C)').fill('37');
  await save.press('Enter');
  await expect(page.getByRole('heading', { name: 'Observation saved' })).toBeVisible();
  await expect(page.locator('#score-result')).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(375);
});
