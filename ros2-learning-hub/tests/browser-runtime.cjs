/* 浏览器验收依赖解析：支持标准安装、显式模块路径和本机捆绑运行库。 */
const path=require('node:path'),os=require('node:os');
const candidates=[process.env.PLAYWRIGHT_MODULE,'playwright','playwright-core',path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core')].filter(Boolean);
let runtime;
for(const candidate of candidates){try{runtime=require(candidate);break;}catch(error){if(error.code!=='MODULE_NOT_FOUND')throw error;}}
if(!runtime)throw new Error('浏览器验收需要 Playwright；请安装或设置 PLAYWRIGHT_MODULE，运行步骤见 README。');
module.exports=runtime;
