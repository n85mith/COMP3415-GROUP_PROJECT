const { test, expect } = require('@playwright/test');

const NORMAL = {
  respiratory_rate: 16, spo2: 98, supplemental_oxygen: false, systolic_bp: 120,
  pulse: 70, consciousness: 'A', temperature: 37.0,
};

async function signIn(page, username = 'nurse') {
  const form = page.locator('#login-form');
  await form.getByLabel('Username', { exact: true }).fill(username);
  await form.getByLabel('Password', { exact: true }).fill('password123');
  await form.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();
}

async function signOut(page) {
  await page.getByRole('button', { name: 'Sign Out' }).click();
  await expect(page.locator('#login-form')).toBeVisible();
}

async function seed(request, patient, ...observations) {
  const login = await request.post('/api/login', { data: { username: 'nurse', password: 'password123' } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  expect((await request.post('/api/patients', { data: patient, headers })).status()).toBe(201);
  for (const changes of observations) {
    const res = await request.post('/api/observations', {
      data: { patient_id: patient.patient_id, ...NORMAL, ...changes }, headers,
    });
    expect(res.ok()).toBeTruthy();
  }
}

async function openEscalations(page) {
  await page.getByRole('navigation', { name: 'Workspace' }).getByRole('button', { name: 'Escalations' }).click();
  await expect(page.getByRole('heading', { name: 'Open Escalations' })).toBeFocused();
}

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test.afterEach(async ({ request }) => {
  const login = await request.post('/api/login', { data: { username: 'clinician', password: 'password123' } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const open = await (await request.get('/api/escalations', { headers })).json();
  for (const escalation of open) {
    await request.post(`/api/escalations/${escalation.id}/acknowledge`, {
      data: { response_note: 'Closed by test clean-up' }, headers,
    });
  }
});

test('nurse raises an escalation and a charge nurse acknowledges it with a response note', async ({ page, request }) => {
  await seed(request, { patient_id: 'P-401', name: 'Synthetic High', ward: 'Ward E', bed: '01' });
  await signIn(page);
  await page.getByRole('button', { name: 'Record observation for P-401' }).click();
  await page.getByLabel('Respiratory rate (breaths/min)').fill('25');
  await page.getByLabel('SpO2 (%)').fill('98');
  await page.getByLabel('Supplemental oxygen?').selectOption('false');
  await page.getByLabel('Systolic BP (mmHg)').fill('120');
  await page.getByLabel('Pulse (beats/min)').fill('135');
  await page.getByLabel('Consciousness').selectOption('V');
  await page.getByLabel('Temperature (°C)').fill('37');
  await page.getByRole('button', { name: 'Save & Score' }).click();
  await expect(page.getByText('Escalation raised')).toBeVisible();
  await signOut(page);

  await signIn(page, 'clinician');
  await openEscalations(page);
  const row = page.locator('#esc-list tr', { hasText: 'P-401' });
  await expect(row).toHaveClass(/esc-High/);
  await expect(row).toContainText('Synthetic High');
  await expect(row).toContainText('Ward E, bed 01');

  const respond = row.getByRole('button', { name: 'Respond to escalation for P-401' });
  await respond.click();
  const note = page.getByLabel('Clinical action / response note');
  await expect(note).toBeFocused();
  await page.getByRole('button', { name: 'Confirm & Acknowledge' }).click();
  await expect(page.locator('#ack-error')).toHaveText('Enter a clinical response note before confirming.');

  await note.fill('Reviewed at bedside, outreach team called');
  await page.getByRole('button', { name: 'Confirm & Acknowledge' }).click();
  await expect(page.locator('#ack-panel')).toBeHidden();
  await expect(page.getByRole('heading', { name: 'Open Escalations' })).toBeFocused();
  await expect(page.locator('#esc-list tr', { hasText: 'P-401' })).toHaveCount(0);

  await page.getByLabel('Status', { exact: true }).selectOption('Acknowledged');
  await expect(page.getByRole('heading', { name: 'Acknowledged Escalations' })).toBeVisible();
  const done = page.locator('#esc-list tr', { hasText: 'P-401' });
  await expect(done).toContainText('Acknowledged');
  await expect(done).toContainText('clinician: Reviewed at bedside, outreach team called');
  await expect(done.getByRole('button')).toHaveCount(0);
});

test('cancelling the response panel returns focus to the Respond button', async ({ page, request }) => {
  await seed(request, { patient_id: 'P-451', name: 'Synthetic Cancel', ward: 'Ward E', bed: '05' },
    { consciousness: 'C' });
  await signIn(page, 'clinician');
  await openEscalations(page);
  const respond = page.getByRole('button', { name: 'Respond to escalation for P-451' });
  await respond.click();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.locator('#ack-panel')).toBeHidden();
  await expect(respond).toBeFocused();
});

test('nurses do not see the escalation inbox', async ({ page }) => {
  await signIn(page);
  const nav = page.getByRole('navigation', { name: 'Workspace' });
  await expect(nav.getByRole('button', { name: 'Escalations' })).toHaveCount(0);
});

test('ward list flags a patient whose next observation is overdue', async ({ page, request }) => {
  await seed(request, { patient_id: 'P-501', name: 'Synthetic Due', ward: 'Ward O', bed: '01' }, {});
  await page.clock.install();
  await page.reload();
  await signIn(page);
  await page.getByLabel('Filter by ward').selectOption('Ward O');
  const row = page.locator('#ward-list tbody tr', { hasText: 'P-501' });
  await expect(row).not.toContainText('OVERDUE');
  await expect(row).not.toHaveClass(/row-overdue/);

  await page.clock.setSystemTime(Date.now() + 13 * 60 * 60 * 1000);
  await page.getByLabel('Filter by ward').selectOption('');
  await page.getByLabel('Filter by ward').selectOption('Ward O');
  await expect(row).toContainText('OVERDUE');
  await expect(row).toHaveClass(/row-overdue/);
});

test('trend shows each observation score with a text alternative and returns focus on close', async ({ page, request }) => {
  await seed(request, { patient_id: 'P-601', name: 'Synthetic Trend', ward: 'Ward T', bed: '01' },
    {}, { consciousness: 'C' });
  await signIn(page);
  const trend = page.getByRole('button', { name: 'Show score trend for P-601' });
  await trend.click();
  await expect(page.getByRole('heading', { name: 'NEWS2 Score Trend - P-601' })).toBeFocused();
  const chart = page.getByRole('img', { name: /NEWS2 scores over time/ });
  await expect(chart).toHaveAccessibleName(/: 0 \(Low\), .*: 3 \(Low-medium\)$/);
  await expect(page.getByText('Showing 2 observation(s).')).toBeVisible();

  await page.getByRole('button', { name: 'Close trend' }).click();
  await expect(page.locator('#trend-panel')).toBeHidden();
  await expect(trend).toBeFocused();
});

test('patient text is shown as text, never run as markup or script', async ({ page, request }) => {
  const payload = '<img src=x onerror="window.__xss = 1">';
  const id = `P-7'"X`;
  await seed(request, { patient_id: id, name: payload, ward: 'Ward X', bed: '01' }, { consciousness: 'U' });
  await signIn(page, 'clinician');
  await openEscalations(page);

  const row = page.locator('#esc-list tr', { hasText: payload });
  await expect(row).toBeVisible();
  await expect(page.locator('#esc-list img')).toHaveCount(0);
  await row.getByRole('button', { name: `Respond to escalation for ${id}` }).click();
  await expect(page.locator('#ack-target-info')).toContainText(`for patient ${id}`);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});
