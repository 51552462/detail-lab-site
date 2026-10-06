/* Content/branch checks in a JS VM, not a browser or evidence of a customer outcome. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const files = ['owner-structure-check.html', 'industry-self-check.html', 'guide-self-check.html', 'trainer-self-check.html'];
let checks = 0;
for (const file of files) {
  const html = fs.readFileSync(path.join(root, file), 'utf8');
  const code = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { innerHTML: '', textContent: '', value: '', classList: { add(){}, remove(){} }, querySelector(){ return null; } });
    return nodes.get(id);
  };
  let copied = '';
  const context = vm.createContext({
    document: { getElementById: node, addEventListener(){} },
    navigator: { clipboard: { writeText(text){ copied = text; return Promise.resolve(); } } },
    setTimeout(){ return 0; }
  });
  vm.runInContext(code, context, { filename: file });
  const run = s => vm.runInContext(s, context);
  assert.equal(run('QUESTIONS.length'), 12);
  assert.equal(run('QUESTIONS.every(q => q.options.length === 5 && q.options[4].s === null)'), true);
  assert.equal(run('QUESTIONS.filter(q => Number.isInteger(q.cat) && q.cat >= 0 && q.cat < CATEGORIES.length).length'), 12);
  for (const choice of [0, 3, 4]) {
    run('startQuiz()');
    for (let i = 0; i < 12; i++) run(`answer(${choice})`);
    const a = JSON.parse(run('JSON.stringify(analyze())'));
    assert.equal(a.noneKnown, choice === 4);
    assert.equal(a.allBest, choice === 0);
    assert.equal(a.unknown, choice === 4 ? 12 : 0);
    for (const id of ['dl-keep', 'dl-before', 'dl-stop']) node(id).value = '가상 검증 기록: ' + id;
    for (const id of ['record-case', 'record-action', 'record-review']) node(id).value = '가상 처리 기록: ' + id;
    run('copyResult()');
    for (const id of ['dl-keep', 'dl-before', 'dl-stop']) assert.ok(copied.includes('가상 검증 기록: ' + id), `${file}: evidence survives copy`);
    assert.ok(node('screen').innerHTML.includes('바꾸기 전에 지킬 점'));
    assert.ok(node('screen').innerHTML.includes('바꾸기 전 기록과 다시 볼 것'));
    const texts = JSON.parse(run('JSON.stringify(state.texts)'));
    for (const t of texts) assert.ok(copied.includes(t), `${file}: original answer survives copy`);
    if (choice === 4) assert.ok(copied.includes('실제 사례') || copied.includes('확인 전'));
    checks++;
  }
  run('state.answers.fill(null); state.answers[0] = 0;');
  const mixed = JSON.parse(run('JSON.stringify(analyze())'));
  assert.equal(mixed.focus, run('QUESTIONS[0].cat'));
  assert.equal(mixed.unknown, 11);
  assert.equal(mixed.noneKnown, false);
  assert.equal(mixed.allBest, false);
  run('renderResult()');
  run('copyResult()');
  assert.ok(copied.includes('11개는 비교에서 제외'));
  if (file !== 'trainer-self-check.html') {
    assert.ok(run('selectionBasis(analyze())').includes(run('QUESTIONS[0].text')));
  }
  run('state.answers.fill(null); state.answers[0] = 3; renderResult(); copyResult();');
  assert.ok(copied.includes('확인한 일부 답만으로 전체 상태를 판단하지 않습니다.'));
  assert.ok(!node('screen').innerHTML.includes('undefined'));
  checks += 2;
}
const matching = fs.readFileSync(path.join(root, 'matching-self-check.html'), 'utf8');
assert.ok(matching.includes('${agreementBox()}'));
assert.ok(matching.includes('...BEFORE_AGREEMENT'));
assert.equal((matching.match(/const BEFORE_AGREEMENT = \[[\s\S]*?\n\];/)[0].match(/^  "/gm) || []).length, 3);
console.log(`OK: 48 scenario questions; ${checks} scored/unknown/mixed VM branches; preservation and evidence copy; 3 matching prompts. Browser/visual review not included.`);
