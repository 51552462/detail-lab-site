/* Browser acceptance tests for the SYN-only loopback harness. Never targets Render. */
const {chromium, expect} = require('@playwright/test');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
const out=path.resolve('ops-flow-artifacts');fs.mkdirSync(out,{recursive:true});
const report={synthetic_only:true,sha:process.env.GITHUB_SHA||'local',flows:[],screens:[],errors:[]};
const flow=(width,name,detail={})=>report.flows.push({width,name,...detail});
async function boot(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'detail-lab-ops-browser-'));
 const child=spawn('python3',['-m','internal.ops_mvp.server','--root',root,'--port','0'],{stdio:['ignore','pipe','pipe']});
 const config=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('server startup timeout')),20000);child.stdout.on('data',chunk=>{text+=chunk;const line=text.split('\n')[0];try{const data=JSON.parse(line);clearTimeout(timer);resolve(data);}catch{}});child.once('exit',code=>reject(new Error(`server exited ${code}`)));});
 return {root,child,url:config.url,keys:JSON.parse(fs.readFileSync(config.test_credentials,'utf8'))};
}
async function login(page,url,key){await page.goto(url);await page.locator('#token').fill(key);await page.getByRole('button',{name:'시험실 열기',exact:true}).click();await expect(page.locator('#workspace')).toBeVisible();}
async function shot(page,width,name,anchor='#content'){await page.locator(anchor).first().evaluate(el=>el.scrollIntoView({block:'start'}));const file=`${width}-${name}.png`;await page.screenshot({path:path.join(out,file)});report.screens.push(file);const dims=await page.evaluate(()=>({vw:innerWidth,sw:document.documentElement.scrollWidth}));if(dims.sw>dims.vw)throw new Error(`${name}: horizontal overflow ${dims.sw}/${dims.vw}`);}
async function tab(page,key){await page.locator(`[data-tab="${key}"]`).click();}
async function rendered(page,response){const data=await response.json();await expect(page.locator('[data-render-event]')).toHaveAttribute('data-render-event',String(data.events.at(-1)?.id||0));}
async function open(page){const listed=page.waitForResponse(r=>r.url().endsWith('/api/cases')&&r.request().method()==='GET');await page.locator('#refresh').click();await listed;await expect(page.locator('.case-link')).toHaveCount(1);const fresh=page.waitForResponse(r=>/\/api\/cases\/SYN-CASE-[a-f0-9]+$/.test(r.url())&&r.request().method()==='GET');await page.locator('.case-link').click();await rendered(page,await fresh);}
async function post(page,action,click,status=200){const response=page.waitForResponse(r=>r.url().endsWith(action)&&r.request().method()==='POST');const fresh=status<400&&action!=='/api/cases'?page.waitForResponse(r=>/\/api\/cases\/SYN-CASE-[a-f0-9]+$/.test(r.url())&&r.request().method()==='GET').catch(()=>null):null;await click();const r=await response;const body=await r.json();if(r.status()!==status)throw new Error(`POST ${action}: expected ${status}, got ${r.status()}, error ${body.error||'unknown'}`);if(fresh){const result=await fresh;if(!result)throw new Error('case refresh missing');await rendered(page,result);}else if(status>=400)await expect(page.locator('#message')).toHaveAttribute('role','alert');return body;}
async function state(page,value,status=200){await tab(page,'overview');await page.locator('#target').selectOption(value);await post(page,'/state',()=>page.locator('#state-form button').click(),status);}
async function run(width,browser){
 const server=await boot();const contexts=[];const pages=[];
 try{
  for(let i=0;i<3;i++){const ctx=await browser.newContext({viewport:{width,height:900}});contexts.push(ctx);const p=await ctx.newPage();p.on('pageerror',e=>report.errors.push({width,error:e.message}));pages.push(p);}
  const [client,operator,other]=pages;
  await client.goto(server.url);await shot(client,width,'login','#login');
  await login(client,server.url,server.keys['SYN-OWNER-A']);
  await client.getByRole('button',{name:'합성 예시 채우기',exact:true}).click();await client.locator('#synthetic-confirm').check();
  await client.locator('#I01').focus();await client.keyboard.press('Tab');await expect(client.locator('#I02')).toBeFocused();flow(width,'keyboard labelled inputs');
  await client.locator('#save-draft').check();await client.locator('#I04').fill('합성 사례: 교대 완료를 다음 담당자가 다시 물었다.');
  await client.reload();await expect(client.locator('#I04')).toHaveValue('합성 사례: 교대 완료를 다음 담당자가 다시 물었다.');await client.locator('#synthetic-confirm').check();flow(width,'opt-in draft restores in same tab');
  await shot(client,width,'intake-start');
  await client.locator('#I09').fill('actual@nonexistent.invalid');
  await post(client,'/api/cases',()=>client.locator('#submit-intake').click(),400);await expect(client.locator('#receipt')).toBeEmpty();await expect(client.locator('#I04')).toHaveValue(/합성/);
  await shot(client,width,'intake-personal-data-error','#I09');flow(width,'personal-data error keeps input and no receipt');
  await client.locator('#I09').fill('owner@example.invalid');
  await client.route('**/api/cases',route=>route.request().method()==='POST'?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'STORAGE_UNAVAILABLE',completed:false})}):route.continue());
  await post(client,'/api/cases',()=>client.locator('#submit-intake').click(),503);await expect(client.locator('#receipt')).toBeEmpty();flow(width,'storage failure is not completion');
  await client.unroute('**/api/cases');
  const receipt=await post(client,'/api/cases',()=>client.locator('#submit-intake').click(),201);await expect(client.locator('#receipt')).toContainText(receipt.id);
  const duplicate=await post(client,'/api/cases',()=>client.locator('#submit-intake').click());expect(duplicate.id).toBe(receipt.id);expect(duplicate.duplicate).toBe(true);await expect(client.locator('.case-link')).toHaveCount(1);flow(width,'retry and duplicate share one receipt');
  await shot(client,width,'receipt','#receipt');
  await login(operator,server.url,server.keys['SYN-OPERATOR']);await open(operator);await operator.locator('#view-contact').click();await expect(operator.locator('#private-contact')).toContainText('owner@example.invalid');await operator.locator('#hide-contact').click();await expect(operator.locator('#private-contact')).toBeEmpty();flow(width,'operator-only contact read is explicit and closable');
  for(const target of ['reviewing','eligible','interview_scheduled'])await state(operator,target);
  await expect(operator.locator('#content')).toContainText('사업 이해 인터뷰');await shot(operator,width,'interview-task');flow(width,'review states create one interview task');
  await tab(operator,'interview');await operator.locator('#fill-interview').click();await post(operator,'/interview',()=>operator.locator('#interview-form button').click());
  await shot(operator,width,'interview-card');await open(client);await tab(client,'interview');await post(client,'/interview/confirm',()=>client.locator('[data-act="confirm-interview"]').click());flow(width,'13-field interview and separate client fact confirmation');
  await open(operator);await tab(operator,'interview');await operator.locator('#fill-diagnosis').click();await shot(operator,width,'diagnosis-module','#D05_reason');
  await post(operator,'/diagnosis',()=>operator.locator('#diagnosis-form button').last().click());flow(width,'goal-specific diagnostic branch');
  await operator.getByText('검토한 합성 자료 발췌 등록',{exact:true}).click();await post(operator,'/evidence',()=>operator.locator('#evidence-form button').click(),201);
  await operator.locator('#kind').selectOption('F');await operator.locator('#statement').fill('합성 기준표 발췌에 완료 칸이 없다.');await operator.locator('#evidence_id').selectOption({index:1});await post(operator,'/claims',()=>operator.locator('#claim-form button').click(),201);
  await operator.locator('#kind').selectOption('H');await operator.locator('#statement').fill('완료 뜻의 차이가 누락에 영향을 줄 수 있다.');await operator.locator('#falsification').fill('기준을 같게 이해해도 같은 누락이 발생하는가?');await post(operator,'/claims',()=>operator.locator('#claim-form button').click(),201);
  await shot(operator,width,'facts-and-hypothesis','#claim-form');flow(width,'reviewed evidence F and falsifiable H remain separate');
  await tab(operator,'goals');await operator.locator('#fill-goal').click();await post(operator,'/goals',()=>operator.locator('#goal-form button').click(),201);
  await shot(operator,width,'goal-version');await post(operator,'/goals/approve',()=>operator.locator('[data-act="approve-goal"]').click());
  for(const target of ['proposal','customer_decision'])await state(operator,target);
  await state(operator,'in_progress',409);await expect(operator.locator('#message')).toContainText('같은 목표 버전');await shot(operator,width,'dual-approval-guard','#state-form');flow(width,'project cannot start before dual approval');
  await open(client);await tab(client,'goals');await post(client,'/goals/approve',()=>client.locator('[data-act="approve-goal"]').click());await open(operator);await state(operator,'in_progress');flow(width,'same goal version approved by client and operator');
  await tab(operator,'experiments');
  for(const [name,value]of Object.entries({reason:'한 업무의 완료 기준 차이를 작게 시험',action:'합성 인계표에 완료 칸 추가',owner:'합성 현장 책임자',user_role:'합성 교대 담당',risk:'추가 입력 부담',rollback:'이전 기준표 v1 복귀'}))await operator.locator(`#experiment-form [name="${name}"]`).fill(value);
  await post(operator,'/experiments',()=>operator.locator('#experiment-form button').click(),201);
  await open(client);await tab(client,'experiments');await post(client,'/experiments/approve',()=>client.locator('[data-approve-exp]').click());
  await open(operator);await tab(operator,'experiments');await operator.getByText('실제 사용·미사용·반응 기록',{exact:true}).click();await post(operator,'/observations',()=>operator.locator('#observation-form button').click());await shot(operator,width,'observed-use');flow(width,'client-authorized experiment and use vs reaction record');
  await open(client);await tab(client,'experiments');await post(client,'/decisions',()=>client.locator('#decision-form button').click());flow(width,'client decides modify with handover and next date');
  await open(operator);await tab(operator,'reports');const csv=await operator.request.get(server.url+'/api/catalog').then(r=>r.json()).then(x=>x.fixtures.csv);
  await operator.locator('#upload-file').setInputFiles({name:'extra-column.csv',mimeType:'text/csv',buffer:Buffer.from(csv.replace('row_key,','employee_name,row_key,'))});
  await post(operator,'/uploads',()=>operator.locator('#upload-form button').click(),400);flow(width,'unexpected file columns rejected');
  await operator.locator('#upload-file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await post(operator,'/uploads',()=>operator.locator('#upload-form button').click(),201);
  await shot(operator,width,'upload-review');await operator.locator('[data-preview-source]').click();await expect(operator.locator('.preview-rows li')).toHaveCount(14);await shot(operator,width,'upload-preview','.preview-rows');flow(width,'operator sees pending rows and units before approval');await post(operator,'/reports',()=>operator.locator('#report-form button').click(),409);flow(width,'pending source cannot enter report');
  await operator.locator('[data-preview-source]').click();await expect(operator.locator('.preview-rows li')).toHaveCount(14);await post(operator,'/uploads/review',()=>operator.locator('[data-review-source][data-approve="true"]').click());
  await post(operator,'/reports',()=>operator.locator('#report-form button').click(),201);await expect(operator.locator('.report-total')).toHaveText(['2026-10-05 · 21건','2026-10-12 · 7건']);
  await shot(operator,width,'weekly-report','.report-total');flow(width,'weekly numbers 21 and 7 trace back to 14 synthetic rows');
  await open(client);await tab(client,'reports');await expect(client.locator('.report-total')).toHaveCount(0);flow(width,'draft report withheld from client');
  await post(operator,'/reports/approve',()=>operator.locator('[data-approve-report]').click());
  const downloadPromise=operator.waitForEvent('download');await operator.locator('[data-download-report]').click();const download=await downloadPromise;const downloadPath=await download.path();const final=JSON.parse(fs.readFileSync(downloadPath,'utf8'));expect(final.body.groups.map(g=>g.total)).toEqual(['21','7']);flow(width,'approved report download preserves source trace');
  await open(client);await tab(client,'reports');await expect(client.locator('.report-total')).toHaveCount(2);flow(width,'approved report available to owning client');
  // A real XLSX file generated locally by openpyxl exercises the same upload endpoint.
  const {execFileSync}=require('node:child_process');const xlsx=path.join(server.root,'changed.xlsx');
  execFileSync('python3',['-c',`import csv,io,sys\nfrom openpyxl import Workbook\nfrom internal.ops_mvp.scenario import csv_data\nw=Workbook()\nfor row in csv.reader(io.StringIO(csv_data(delta=1).decode())):w.active.append(row)\nw.save(sys.argv[1]);w.close()`,xlsx]);
  await client.locator('#upload-file').setInputFiles(xlsx);await post(client,'/uploads',()=>client.locator('#upload-form button').click(),201);flow(width,'changed XLSX creates pending version 2');
  await open(operator);await tab(operator,'reports');await expect(operator.locator('#content')).toContainText('재검수 필요');await shot(operator,width,'stale-report','.report-total');
  await open(client);await tab(client,'reports');await expect(client.locator('.report-total')).toHaveCount(0);flow(width,'changed data invalidates approved report for client');
  await operator.locator('[data-preview-source]').click();await expect(operator.locator('.preview-rows li')).toHaveCount(14);await post(operator,'/uploads/review',()=>operator.locator('[data-review-source][data-approve="true"]').click());await operator.locator('#report_kind').selectOption('monthly');await post(operator,'/reports',()=>operator.locator('#report-form button').click(),201);await expect(operator.locator('.report-total').last()).toHaveText('2026-10 · 42건');
  await post(operator,'/reports/approve',()=>operator.locator('[data-approve-report]').click());await state(operator,'closed');await expect(operator.locator('#content h1')).toHaveText('종료');await shot(operator,width,'handover-closed');flow(width,'reviewed experiment and current approved report permit handover');
  await login(other,server.url,server.keys['SYN-OWNER-B']);expect((await other.request.get(server.url+`/api/cases/${receipt.id}`)).status()).toBe(404);await expect(other.locator('.case-link')).toHaveCount(0);flow(width,'tenant B cannot enumerate tenant A case');
  await client.locator('#logout').click();await expect(client.locator('#login')).toBeVisible();expect((await client.request.get(server.url+'/api/cases')).status()).toBe(401);flow(width,'logout revokes the session');
 }finally{for(const c of contexts)await c.close();server.child.kill('SIGTERM');fs.rmSync(server.root,{recursive:true,force:true});}
}
(async()=>{let browser;try{browser=await chromium.launch({headless:true});for(const width of [360,1280])await run(width,browser);expect(report.errors).toEqual([]);}catch(e){report.failure=e.stack;process.exitCode=1;}finally{if(browser)await browser.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({flows:report.flows.length,screens:report.screens.length,errors:report.errors.length,failure:report.failure||null}));}})();
