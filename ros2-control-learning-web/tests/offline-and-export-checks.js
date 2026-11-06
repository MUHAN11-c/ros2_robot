async (page) => {
  const result={};
  const local=await page.context().newPage();
  try {
    await local.goto('file:///home/mu/Desktop/ros2_jazzy_tracked_refs/ros2-control-learning-web/index.html#architecture');
    await local.locator('[data-node="system"]').click();
    if(await local.locator('#component-detail h2').innerText()!=='系统组件')throw new Error('直接打开本地文件时交互失效');
    result.fileEntry='本地文件直接打开，脚本和双语流程图正常';
    await local.evaluate(()=>{location.hash='files';});
    await local.locator('[data-file="yaml"]').click();
    await local.evaluate(()=>{
      Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw new Error('denied')}}});
      document.execCommand=()=>false;
    });
    await local.locator('[data-copy="yaml"]').click();
    const fallback=local.locator('.manual-copy');await fallback.waitFor();
    if(!(await fallback.inputValue()).includes('left_wheel_names'))throw new Error('复制失败时应提供正确的手动选中文本');
    result.clipboardDenied='自动复制被拒绝时可手动选中文本';
  } finally {await local.close();}
  await page.goto('http://127.0.0.1:8765/?export-check='+Date.now()+'#architecture');
  const downloadEvent=page.waitForEvent('download');await page.locator('[data-action="download"]').click();
  const download=await downloadEvent;
  await download.saveAs('/home/mu/Desktop/ros2_jazzy_tracked_refs/ros2-control-learning-web/assets/ros2-control-architecture.svg');
  result.svg=download.suggestedFilename();
  return result;
}
