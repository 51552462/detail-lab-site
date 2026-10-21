/* Reproducible local customer-flow checks. Fixtures contain no real customer data.
 * npm install --no-save playwright@1.62.1 && npx playwright install chromium
 * node .github/scripts/check_customer_flows.cjs [artifact directory]
 * Screenshots/traces are generated evidence, not a claim that someone viewed them.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');

const root = path.resolve(__dirname, '../..');
const out = path.resolve(process.argv[2] || path.join(root, 'customer-flow-artifacts'));
const report = { sha: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root }).toString().trim(),
  startedAt: new Date().toISOString(), environment: 'local static preview; synthetic inputs; no form submissions',
  visualReview: 'not performed by this script', sources: {}, checks: [], screenshots: [], errors: [] };
const pages = ['index.html', 'center.html', 'industry.html', 'employee-guide.html', 'matching.html', 'business.html', 'feedback.html',
  'owner-structure-check.html', 'industry-self-check.html', 'guide-self-check.html',
  'trainer-self-check.html', 'matching-self-check.html', 'areas.css', 'og-home.png'];
const record = (viewport, tool, branch, details) => {
  const item = { viewport, tool, branch, details };
  report.checks.push(item); console.log(JSON.stringify(item));
};
const mime = { '.html': 'text/html', '.css': 'text/css', '.png': 'image/png', '.webp': 'image/webp' };
let browser, server;

async function copied(page, button, filename) {
  await page.evaluate(() => navigator.clipboard.writeText(''));
  await button.click();
  await page.waitForFunction(() => /복사/.test(document.querySelector('#toast, #decision-status')?.textContent || ''));
  await page.waitForFunction(async () => (await navigator.clipboard.readText()).length > 60);
  const text = await page.evaluate(() => navigator.clipboard.readText());
  assert.ok(text.length > 60, 'copy must produce result text');
  await fs.writeFile(path.join(out, filename), text);
  return text;
}

async function screenshotResult(page, viewport, name, selector = '#screen .result') {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => !document.querySelector('#toast.show'));
  await page.waitForTimeout(350);
  const target = page.locator(selector);
  const box = await target.boundingBox();
  assert.ok(box, `visible result: ${name}`);
  const scrollY = await page.evaluate(() => window.scrollY);
  const top = box.y + scrollY;
  const bottom = top + box.height;
  const headerGap = await page.evaluate(() => {
    const header = document.querySelector('.site-header');
    return header && getComputedStyle(header).position === 'fixed' ? header.getBoundingClientRect().height + 24 : 24;
  });
  let i = 0;
  for (let y = Math.max(0, top - headerGap); y < bottom; y += 660) {
    await page.evaluate(y => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo({ top: y, behavior: 'instant' }); }, y);
    await page.waitForFunction(y => Math.abs(window.scrollY - Math.min(y, document.documentElement.scrollHeight - innerHeight)) < 2, y);
    const actualY = await page.evaluate(() => window.scrollY);
    const filename = `${viewport}-${name}-${String(++i).padStart(2, '0')}.png`;
    await page.screenshot({ path: path.join(out, filename) });
    report.screenshots.push({ viewport, name, filename, scrollY: actualY });
    if (actualY + 800 >= bottom) break;
  }
}

async function noOverflow(page) {
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'horizontal overflow');
}

async function landingPages(page, origin, viewport) {
  for (const [file, heading, primary, detail] of [
    ['index.html', '운영하면서 걸리는 일', '/business.html#contact', '.category-grid'],
    ['center.html', '작은 결정도', '/owner-structure-check.html', '.path-grid'],
    ['industry.html', '사장님께 확인할게요', '/industry-self-check.html', '.example-output'],
    ['employee-guide.html', '면접 때 들은 조건', '#worksheet', '.example-output'],
    ['matching.html', '저녁 가능', '/matching-self-check.html?role=member', '.example-output'],
    ['business.html', '운영 상황부터 듣고', '#contact', '.business-steps'],
    ['feedback.html', '설명이 헷갈렸나요', 'https://wary-crocus-59c.notion.site/1ee8a0d648944e8abf0d7da9897ae80e', '.response-card']
  ]) {
    await page.goto(`${origin}/${file}`);
    await page.evaluate(async () => {
      await document.fonts.ready;
      window.scrollTo(0, 0);
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    assert.ok((await page.locator('h1').innerText()).includes(heading));
    assert.deepEqual(await page.locator('#site-nav a').evaluateAll(links => links.map(link => link.getAttribute('href'))), ['/business.html#contact','/#process','/#tools','/center.html'], 'unified entry and retained beta in the main menu');
    const action = file === 'index.html' ? page.locator('.brand-hero a[href="/business.html#contact"]') : page.locator(`a[href="${primary}"]`).first();
    assert.ok(await action.isVisible());
    assert.ok((await action.boundingBox()).height >= 44, `primary action must be fully readable and tappable: ${file}`);
    await noOverflow(page);

    const name = file.replace('.html', '');
    // Element screenshots scroll the page; restore the actual first screen before saving its evidence.
    await page.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo({ top: 0, behavior: 'instant' }); });
    await page.waitForFunction(() => window.scrollY === 0);
    const first = `${viewport}-page-${name}-hero.png`;
    await page.screenshot({ path: path.join(out, first) });
    report.screenshots.push({ viewport, name: `page-${name}-hero`, filename: first, scrollY: 0 });
    if (file === 'index.html') {
      assert.deepEqual(await page.locator('.category-card h3').allTextContents(), ['센터 자가점검','가게·교대 점검','직장 선택 기록','수업 준비 도구']);
      const availableServices = await page.locator('#privacy-detail dt').allTextContents();
      for (const service of ['전 업종 운영 문의','센터 무료 베타','무료 자가점검·기록지','맞춤 적용·정기 관리','고객별 데이터 시스템']) {
        assert.ok(availableServices.includes(service), `existing service scope must remain: ${service}`);
      }
      const trialEntry = page.locator('#privacy-detail dd').filter({ has: page.locator('a[href="https://detail-lab-ops-trial.onrender.com/"]') });
      assert.ok((await trialEntry.innerText()).includes('준비된 가상 자료만 사용'), 'hosted rehearsal must disclose fixture-only scope');
      assert.ok((await trialEntry.innerText()).includes('실제 문의 접수나 고객 자료 저장은 하지 않습니다'), 'rehearsal must not imply real customer intake');
      assert.equal(await page.locator('#people .offer-steps li').count(), 4);
      const people = `${viewport}-page-index-people.png`;
      await page.locator('#people').screenshot({ path: path.join(out, people), style: '.site-header, .skip-link { visibility: hidden !important; }' });
      report.screenshots.push({ viewport, name: 'page-index-people', filename: people, selector: '#people' });
    }
    const section = `${viewport}-page-${name}-detail.png`;
    await page.locator(detail).screenshot({ path: path.join(out, section), style: '.site-header, .skip-link { visibility: hidden !important; }' });
    report.screenshots.push({ viewport, name: `page-${name}-detail`, filename: section, selector: detail });
    if (file === 'index.html') {
      assert.equal(await page.locator('.dl-concern').count(), 7);
      assert.equal(await page.locator('#faq details').count(), 11);
      assert.equal(await page.locator('form, input, textarea').count(), 0, 'no new personal-data intake');
      for (const section of ['#concerns','#philosophy','#system','#about','#faq']) {
        await screenshotResult(page, viewport, 'new-home-' + section.slice(1), section);
      }
      const question = page.locator('#faq summary').first();
      await question.focus();
      await page.keyboard.press('Enter');
      assert.ok(await page.locator('#faq details').first().getAttribute('open') !== null);
      await noOverflow(page);
      record(viewport, 'unified-home', '7 concerns; 11 FAQs; keyboard disclosure', 'new content and no added intake');
    }
    if (file === 'business.html') {
      assert.equal(await page.locator('.dl-case').count(), 4);
      for (const id of ['case-sales','case-away','case-team','case-brand']) {
        assert.equal(await page.locator('#' + id + ' dt').count(), 6);
        await screenshotResult(page, viewport, 'new-' + id, '#' + id);
      }
      assert.ok((await page.locator('#cases').innerText()).includes('실제 고객'));
      const actions = await page.locator('.subhero-actions .button').all();
      const firstBox = await actions[0].boundingBox(), secondBox = await actions[1].boundingBox();
      assert.ok(Math.max(secondBox.x - firstBox.x - firstBox.width, secondBox.y - firstBox.y - firstBox.height) >= 8, 'hero buttons need a visible gap');
      const contrast = await page.evaluate(() => {
        const rgb = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
        const light = color => rgb(color).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
        const a = light(getComputedStyle(document.querySelector('.dl-contact-prompts')).color);
        const b = light(getComputedStyle(document.querySelector('.action-panel')).backgroundColor);
        return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      });
      assert.ok(contrast >= 4.5, 'contact question contrast');
      await page.locator('[data-copy-intake]').click();
      await page.waitForFunction(() => document.querySelector('#intake-copy-status').textContent.includes('복사했습니다'));
      assert.ok((await page.evaluate(() => navigator.clipboard.readText())).includes('최근 걸린 한 장면'));
      await page.evaluate(() => Object.defineProperty(navigator.clipboard, 'writeText', { configurable: true, value: async () => { throw new Error('synthetic clipboard denial'); } }));
      await page.locator('[data-copy-intake]').click();
      await page.waitForFunction(() => document.querySelector('#intake-copy-status').textContent.includes('직접 선택'));
      assert.ok(await page.locator('.dl-intake-template').getAttribute('open') !== null);
      await noOverflow(page);
      await screenshotResult(page, viewport, 'new-contact', '#contact');
      for (const section of ['#deliverables','#responsibility','#data','#market']) {
        await screenshotResult(page, viewport, 'new-' + section.slice(1), section);
      }
      record(viewport, 'service-details', '4 fictional cases; 3 outputs; responsibility; template copy and failure fallback', 'no new submission or file collection');
    }
    const additionalSections = {
      'index.html': ['.brand-criteria', '.category-benefit-preview', '#beta', '#faq'],
      'center.html': ['.founder-context', '#benefit'],
      'industry.html': ['.offer-intro', '.copy-why'],
      'employee-guide.html': ['.offer-intro', '.copy-scene', '.copy-why', '.copy-compare', '.offer-detail', '#decision-next-steps'],
      'business.html': ['.offer-intro', '.copy-why', '#contact', '.copy-faq']
    }[file] || [];
    for (const [index, selector] of additionalSections.entries()) {
      const filename = `${viewport}-page-${name}-answer-${index + 1}.png`;
      await page.locator(selector).screenshot({ path: path.join(out, filename), style: '.site-header, .skip-link { visibility: hidden !important; }' });
      report.screenshots.push({ viewport, name: `page-${name}-answer-${index + 1}`, filename, selector });
    }
    record(viewport, name, 'entry page', 'heading, primary action, horizontal layout and visible detail screenshot');
  }
}

async function centerBenefit(page, origin, viewport) {
  await page.goto(`${origin}/index.html`);
  await page.locator('.category-benefit-preview a').click();
  await page.waitForURL(`${origin}/center.html#benefit`);
  assert.ok(await page.locator('#benefit-title').isVisible());
  assert.ok((await page.locator('#benefit').innerText()).includes('준비하고 있습니다'));
  assert.ok((await page.locator('#benefit').innerText()).includes('무료 도구'));
  await noOverflow(page);
  await page.locator('.benefit-actions a[href="/matching.html"]').click();
  await page.waitForURL(`${origin}/matching.html`);
  assert.equal(await page.locator('#site-nav a[aria-current="page"]').getAttribute('href'), '/center.html');
  await page.locator('.benefit-backlink').click();
  await page.waitForURL(`${origin}/center.html#benefit`);
  await page.locator('.benefit-actions a[href="/matching-self-check.html?role=member"]').click();
  await page.waitForURL(`${origin}/matching-self-check.html?role=member`);
  assert.ok((await page.locator('.brandline').innerText()).includes('센터 베네핏'));
  await noOverflow(page);
  record(viewport, 'center-benefit', 'home → center benefit → explanation → center → free tool', 'four categories; benefit is prepared inside center; existing free tool and back link remain accessible');
}

async function quiz(page, origin, viewport, filename, tool) {
  const outputs = [];
  for (const choice of [0, 3]) {
    await page.goto(`${origin}/${filename}`);
    await page.locator('button[onclick="startQuiz()"]').click();
    const firstText = await page.locator('.option-btn').nth(choice).innerText();
    await page.locator('.option-btn').nth(choice).click();
    await page.getByRole('button', { name: '← 이전 질문', exact: true }).click();
    assert.equal(await page.locator('.option-btn[aria-pressed="true"]').innerText(), firstText);
    const changed = choice === 0 ? 1 : 2;
    const changedText = await page.locator('.option-btn').nth(changed).innerText();
    await page.locator('.option-btn').nth(changed).click();
    await page.getByRole('button', { name: '← 이전 질문', exact: true }).click();
    assert.equal(await page.locator('.option-btn[aria-pressed="true"]').innerText(), changedText);
    for (let i = 0; i < 12; i++) await page.locator('.option-btn').nth(choice).click();
    assert.equal(await page.locator('.cat-item').count(), 12);
    if (choice === 3 && ['store', 'shift'].includes(tool)) {
      await page.locator('#record-case').fill('가상 테스트: 교대 뒤 예약 문의 재확인');
      await page.locator('#record-action').fill('다음 담당자가 오전 11시까지 답변');
      await page.locator('#record-review').fill('7일 뒤 같은 문의가 돌아온 횟수');
    }
    if (choice === 3 && tool === 'center') {
      await page.locator('#next-check').fill('검증용: 이전 안내를 담당자와 확인');
      await page.locator('#next-action').fill('검증용: 관리자 결정 후 다음 담당자가 안내');
      await page.locator('#next-review').fill('검증용: 다음 주 실제 사용 기록 비교');
    }
    const copy = await copied(page, page.locator('button[onclick="copyResult()"]'), `${viewport}-${tool}-${choice}-copy.txt`);
    if (choice === 3 && ['store', 'shift'].includes(tool)) {
      for (const entry of ['가상 테스트: 교대 뒤 예약 문의 재확인', '다음 담당자가 오전 11시까지 답변', '7일 뒤 같은 문의가 돌아온 횟수']) assert.ok(copy.includes(entry), `${tool} recorded case must survive copying`);
    }
    for (const text of await page.locator('.cat-item .name, .cat-item p').allTextContents()) assert.ok(copy.includes(text.trim()));
    if (tool === 'center') {
      if (choice === 0) assert.ok(!copy.includes('내가 직접 정한 다음 행동'), 'blank notes must not invent an action');
      else for (const entry of ['검증용: 이전 안내를 담당자와 확인','검증용: 관리자 결정 후 다음 담당자가 안내','검증용: 다음 주 실제 사용 기록 비교']) assert.ok(copy.includes(entry));
    }
    outputs.push(copy);
    await noOverflow(page);
    if (choice === 3) {
      if (await page.locator('details.why-box').count()) await page.locator('details.why-box').evaluate(el => { el.open = true; });
      await screenshotResult(page, viewport, tool);
    }
    record(viewport, tool, choice === 0 ? 'first answers' : 'last answers', '12 answers → result → real clipboard; previous answer retained and changed; no horizontal overflow');
  }
  assert.notEqual(outputs[0], outputs[1], 'different answers must not produce identical copied results');
}

async function employee(page, origin, viewport) {
  await page.goto(`${origin}/employee-guide.html#worksheet`);
  await page.locator('#decision-build').click();
  assert.match(await page.locator('#decision-summary').innerText(), /質問|질문 하나|들은 답 하나/);
  await page.locator('#decision-question').fill('검증용 질문: 첫 주 교육은 누가 알려 주나요?');
  await page.locator('#decision-build').click();
  const before = await copied(page, page.locator('#decision-copy'), `${viewport}-employee-before-interview-copy.txt`);
  assert.match(before, /면접 전 준비/);
  await page.locator('#offer-name-A').fill('검증용 A');
  await page.locator('textarea[data-offer="A"][data-topic="0"]').fill('검증용 A 일정: 월·수 근무');
  await page.locator('#decision-build').click();
  const heard = await page.locator('#decision-summary').innerText();
  assert.match(heard, /검증용 A 일정: 월·수 근무 \[들은 말\]/);
  assert.match(heard, /A·검증용 A 들은 말만: “검증용 A 일정: 월·수 근무”라고 들었는데, 문서나 메시지로 확인할 수 있을까요\?/, 'heard-only condition must ask for a document, not repeat the open question');
  assert.match(heard, /급여 산정·정산 시점 \(A·검증용 A 빈칸\): 급여는 어떤 기준으로 계산하고 언제 정산하나요\?/, 'blank condition must keep the open question');
  await copied(page, page.locator('#decision-copy'), `${viewport}-employee-a-copy.txt`);
  await page.locator('input[data-verify="A"][data-topic="0"]').check();
  await page.locator('#show-b').check();
  await page.locator('#offer-name-B').fill('검증용 B');
  await page.locator('textarea[data-offer="B"][data-topic="0"]').fill('검증용 B 일정: 화·목 근무');
  await page.locator('#decision-build').click();
  await page.locator('#next-check').fill('검증용: 당직 횟수를 담당자와 확인');
  await page.locator('#next-action').fill('검증용: 면접 후 받은 조건을 비교');
  await page.locator('#next-review').fill('검증용: 첫 주 실제 당직 기록');
  const both = await copied(page, page.locator('#decision-copy'), `${viewport}-employee-ab-copy.txt`);
  assert.match(both, /검증용 A 일정: 월·수 근무 \[문서·메시지로 확인\]/);
  assert.match(both, /검증용 B 일정: 화·목 근무 \[들은 말\]/);
  assert.match(both, /B·검증용 B 들은 말만: “검증용 B 일정: 화·목 근무”라고 들었는데, 문서나 메시지로 확인할 수 있을까요\?/);
  assert.ok(!both.includes('A·검증용 A 들은 말만'), 'a document-confirmed condition must not be asked again');
  for (const entry of ['검증용: 당직 횟수를 담당자와 확인','검증용: 면접 후 받은 조건을 비교','검증용: 첫 주 실제 당직 기록']) assert.ok(both.includes(entry));
  assert.equal(both, await page.locator('#decision-summary').innerText(), 'employee clipboard equals displayed result');
  await page.waitForFunction(() => {
    const result = document.querySelector('#decision-summary').getBoundingClientRect();
    const header = document.querySelector('.site-header').getBoundingClientRect();
    return result.top >= header.bottom && result.top < innerHeight;
  });
  await noOverflow(page);
  await screenshotResult(page, viewport, 'employee-record', '#decision-summary');
  await page.locator('#show-b').uncheck();
  await page.locator('#next-action').fill('검증용: 수정한 다음 행동');
  const aOnly = await copied(page, page.locator('#decision-copy'), `${viewport}-employee-b-off-copy.txt`);
  assert.ok(!aOnly.includes('검증용 B'));
  assert.ok(aOnly.includes('검증용 A'));
  assert.ok(aOnly.includes('검증용: 수정한 다음 행동'));
  assert.ok(!aOnly.includes('검증용: 면접 후 받은 조건을 비교'));
  record(viewport, 'employee-record', 'empty / before interview / A / A+B / B off', 'heard versus document-confirmed; exact displayed-result/clipboard equality; B removed from result and copy');
}

async function roleQuestions(page, role, day, time, pick = {}) {
  const questions = role === 'member' ? ['지금 목표', '가능한 요일', '가능한 시간대', '주당 몇 회', '설명은', '피드백은', '대면으로']
    : ['가능한 요일', '가능한 시간대', '한 회원', '수업 방식', '피드백은', '맡기 어려운', '대면 가능'];
  for (let i = 0; i < 7; i++) {
    assert.ok((await page.locator('.q-text').innerText()).includes(questions[i]));
    if (questions[i].includes('요일') || questions[i].includes('시간대')) {
      // A multi-choice question must reject an empty selection.
      await page.getByRole('button', { name: '다음', exact: true }).click();
      assert.ok((await page.locator('.q-meta').innerText()).startsWith(`${i + 1} /`));
      await page.getByRole('button', { name: questions[i].includes('요일') ? day : time, exact: true }).click();
      await page.getByRole('button', { name: '다음', exact: true }).click();
      if (i < 6) {
        await page.getByRole('button', { name: '← 이전 질문', exact: true }).click();
        assert.equal(await page.locator('.option-btn[aria-pressed="true"]').innerText(), questions[i].includes('요일') ? day : time);
        await page.getByRole('button', { name: '다음', exact: true }).click();
      }
    } else {
      const options = page.locator('.option-btn');
      const picked = pick[questions[i]] ?? 0;
      if (i === 6) { await options.nth(picked).click(); continue; }
      const chosen = await options.first().innerText();
      await options.first().click();
      await page.getByRole('button', { name: '← 이전 질문', exact: true }).click();
      assert.equal(await page.locator('.option-btn[aria-pressed="true"]').innerText(), chosen);
      await options.nth(1).click();
      await page.getByRole('button', { name: '← 이전 질문', exact: true }).click();
      assert.equal(await page.locator('.option-btn[aria-pressed="true"]').count(), 1);
      await options.nth(picked).click();
    }
  }
}

async function matchingConflict(page, origin, viewport) {
  // Member wants 3+ lessons a week, trainer offers 2; both leave the in-person period undecided.
  await page.goto(`${origin}/matching-self-check.html`);
  await page.getByRole('button', { name: '회원용 시작', exact: true }).click();
  await page.getByRole('button', { name: '시작', exact: true }).click();
  await roleQuestions(page, 'member', '수', '저녁', { '주당 몇 회': 2, '대면으로': 3 });
  await page.locator('#pair-consent').check();
  await page.locator('button[onclick="acceptPair()"]').click();
  await page.getByRole('button', { name: '트레이너 질문 시작', exact: true }).click();
  await page.getByRole('button', { name: '시작', exact: true }).click();
  await roleQuestions(page, 'trainer', '수', '저녁', { '한 회원': 1, '대면 가능': 3 });
  await page.locator('#pair-consent').check();
  await page.locator('button[onclick="acceptPair()"]').click();
  const result = await page.locator('#screen').innerText();
  const copy = await copied(page, page.getByRole('button', { name: '대조 결과 복사하기', exact: true }), `${viewport}-matching-pair-conflict-copy.txt`);
  for (const line of ['회원이 원하는 횟수가 트레이너 가능 횟수보다 많음 · 조율 필요', '기간 확인 필요', '회원이 원하는 횟수는 3회 이상, 트레이너가 가능한 횟수는 2회입니다. 횟수를 어떻게 맞출까요?', '대면 기간이 미정인 쪽은 언제쯤 정할 수 있나요?']) assert.ok(result.includes(line) && copy.includes(line), `conflict line must match the result: ${line}`);
  await noOverflow(page);
  await screenshotResult(page, viewport, 'matching-conflict');
  record(viewport, 'matching', 'matching-frequency-conflict', 'member 3+ vs trainer 2 per week and undecided period: warning, tailored questions, display and clipboard agree');
}

async function matching(page, origin, viewport) {
  for (const overlap of [true, false, 'day-only', 'time-only']) {
    await page.goto(`${origin}/matching-self-check.html`);
    await page.getByRole('button', { name: '회원용 시작', exact: true }).click();
    await page.getByRole('button', { name: '시작', exact: true }).click();
    await roleQuestions(page, 'member', '수', '저녁');
    const member = await copied(page, page.getByRole('button', { name: '내 답만 복사하기', exact: true }), `${viewport}-matching-member-${overlap}-copy.txt`);
    assert.match(member, /회원/);
    await page.locator('button[onclick="acceptPair()"]').click();
    assert.equal(await page.locator('#pair-consent').count(), 1, 'consent must block transition');
    await page.locator('#pair-consent').check();
    await page.locator('button[onclick="acceptPair()"]').click();
    await page.getByRole('button', { name: '트레이너 질문 시작', exact: true }).click();
    await page.getByRole('button', { name: '시작', exact: true }).click();
    await roleQuestions(page, 'trainer', overlap === true || overlap === 'day-only' ? '수' : '목', overlap === true || overlap === 'time-only' ? '저녁' : '오전');
    await copied(page, page.getByRole('button', { name: '내 답만 복사하기', exact: true }), `${viewport}-matching-trainer-${overlap}-copy.txt`);
    await page.locator('button[onclick="acceptPair()"]').click();
    assert.equal(await page.locator('.pair-grid').count(), 0, 'both roles must consent');
    await page.locator('#pair-consent').check();
    await page.locator('button[onclick="acceptPair()"]').click();
    const result = await page.locator('#screen').innerText();
    const copy = await copied(page, page.getByRole('button', { name: '대조 결과 복사하기', exact: true }), `${viewport}-matching-pair-${overlap}-copy.txt`);
    const expected = overlap === true ? '겹치는 요일은 수요일, 겹치는 시간대는 저녁입니다.'
      : overlap === false ? '겹치는 요일이나 시간대가 없습니다.'
      : overlap === 'day-only' ? '겹치는 요일은 수요일이지만 시간대는 겹치지 않습니다.'
      : '겹치는 시간대는 저녁이지만 요일은 겹치지 않습니다.';
    assert.ok(result.includes(expected) && copy.includes(expected));
    const schedule = overlap === true ? '겹치는 요일(수요일)과 시간대(저녁) 안에서, 트레이너의 예약표상 실제로 비어 있는 수업 시간은 언제인가요?'
      : overlap === false ? '겹치는 요일과 시간대가 없습니다. 어느 쪽이 요일이나 시간대를 넓힐 수 있나요?'
      : overlap === 'day-only' ? '겹치는 요일은 수요일뿐이고 시간대가 다릅니다. 그 요일에 서로 맞출 수 있는 시간대가 있나요?'
      : '겹치는 시간대는 저녁뿐이고 요일이 다릅니다. 요일을 하나 더 넓힐 수 있나요?';
    for (const line of [`① ${schedule}`, '② 주당 횟수(둘 다 1회)와 대면 기간(둘 다 1개월)이 서로 가능한가요?', '④ 설명 방식(둘 다 짧고 핵심만)과 피드백 빈도(둘 다 동작마다)가 답한 대로 진행되는지 첫 수업에서 확인해 볼까요?', '③ 수업 장소·비용·변경·취소 기준은 무엇인가요?', '첫 수업 뒤']) assert.ok(result.includes(line) && copy.includes(line), `first-conversation line must match the result: ${line}`);
    assert.ok(copy.includes('수업 예약을 확정하지 않습니다'), 'copy must not imply a confirmed booking');
    assert.equal(await page.locator('.pair-row').count(), 6);
    for (const value of await page.locator('.pair-row span, .pair-row em').allTextContents()) assert.ok(copy.includes(value.trim()));
    await noOverflow(page);
    const caseName = overlap === true ? 'matching-overlap' : overlap === false ? 'matching-no-overlap' : `matching-${overlap}`;
    await screenshotResult(page, viewport, caseName);
    record(viewport, 'matching', caseName, '7 questions for each role; empty multi-answer rejection; previous selections; both consents block; display and clipboard agree');
  }
}

(async () => {
  await fs.mkdir(out, { recursive: true });
  for (const filename of pages) report.sources[filename] = crypto.createHash('sha256').update(await fs.readFile(path.join(root, filename))).digest('hex');
  server = http.createServer(async (req, res) => {
    const filename = path.resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://local').pathname));
    if (!filename.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    try { const data = await fs.readFile(filename); res.writeHead(200, { 'Content-Type': mime[path.extname(filename)] || 'text/plain' }).end(data); }
    catch { res.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const options = { headless: true };
  if (process.env.CHROMIUM_EXECUTABLE_PATH) options.executablePath = process.env.CHROMIUM_EXECUTABLE_PATH;
  browser = await chromium.launch(options);
  for (const width of [360, 1280]) {
    const context = await browser.newContext({ viewport: { width, height: 800 }, permissions: ['clipboard-read', 'clipboard-write'], reducedMotion: 'reduce' });
    await context.route('**/*', route => route.request().url().startsWith(origin) ? route.continue() : route.abort());
    await context.tracing.start({ screenshots: false, snapshots: true, sources: true });
    const page = await context.newPage();
    page.on('pageerror', e => report.errors.push({ viewport: width, url: page.url(), message: e.message }));
    try {
      await landingPages(page, origin, width);
      await centerBenefit(page, origin, width);
      for (const [filename, tool] of [['owner-structure-check.html', 'center'], ['industry-self-check.html', 'store'], ['guide-self-check.html', 'shift'], ['trainer-self-check.html', 'trainer']]) await quiz(page, origin, width, filename, tool);
      await employee(page, origin, width);
      await matching(page, origin, width);
      await matchingConflict(page, origin, width);
    } finally { await context.tracing.stop({ path: path.join(out, `${width}-trace.zip`) }); await context.close(); }
  }
  assert.equal(report.errors.length, 0, 'browser JS errors');
  report.status = 'passed';
})().catch(e => { report.status = 'failed'; report.failure = e.stack; process.exitCode = 1; console.error(e); }).finally(async () => {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  report.finishedAt = new Date().toISOString();
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`Customer flow check: ${report.status}; ${report.checks.length} paths; ${report.screenshots.length} readable screenshot tiles; ${report.errors.length} JS errors`);
});


