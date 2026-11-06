async (page) => {
  await page.goto('http://127.0.0.1:8765/?diagram-check='+Date.now()+'#architecture');
  await page.locator('[data-mode="command"]').click();
  const feedback = await page.evaluate(() => ({
    controllerA: Number(getComputedStyle(document.querySelector('[data-node="controller-a"]')).opacity),
    controllerC: Number(getComputedStyle(document.querySelector('[data-node="controller-c"]')).opacity)
  }));
  if (feedback.controllerA <= feedback.controllerC) {
    throw new Error('命令数据流应突出示例为差速控制器的 A，不能把示例为状态广播器的 C 画成命令写入者');
  }
  await page.locator('[data-mode="state"]').click();
  const actuatorOpacity=await page.locator('[data-node="actuator"]').evaluate(el=>Number(getComputedStyle(el).opacity));
  if(actuatorOpacity<1)throw new Error('状态反馈视图不应排除可读反馈的 Actuator');
  if(await page.locator('path[data-from="actuator"][data-to="state"]').count()!==1)throw new Error('状态视图应显示 Actuator 到 State 的可选反馈连接');
  await page.locator('[data-mode="all"]').click();
  if(await page.locator('path[data-from="actuator"][data-to="state"]').count()!==1)throw new Error('架构全景应包含 Actuator 可选状态导出关系');
  await page.locator('[data-node="actuator"]').click();
  const explanation=await page.locator('#component-detail').innerText();
  if(!explanation.includes('状态接口')||!explanation.includes('省略'))throw new Error('执行器说明应解释状态反馈与可省略的读取能力');
  return {passed:true,feedback};
}
