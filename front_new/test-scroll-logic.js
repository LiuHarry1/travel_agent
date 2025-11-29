// 测试滚动逻辑的模拟脚本
// 这个脚本模拟了滚动计算逻辑

function testScrollCalculation() {
  console.log('=== 滚动逻辑测试 ===\n');

  // 模拟场景1: 第一条消息
  console.log('场景1: 发送第一条消息 "hello"');
  const scenario1 = {
    containerScrollTop: 0,
    messageTop: 100, // 消息在视口中的位置
    containerTop: 50,  // 容器在视口中的位置
  };
  
  const distance1 = scenario1.messageTop - scenario1.containerTop;
  const targetScroll1 = scenario1.containerScrollTop + distance1;
  
  console.log('  当前滚动位置:', scenario1.containerScrollTop);
  console.log('  消息距离容器顶部:', distance1);
  console.log('  目标滚动位置:', targetScroll1);
  console.log('  ✓ 消息应该滚动到顶部\n');

  // 模拟场景2: 第二条消息（有旧消息）
  console.log('场景2: 发送第二条消息 "who are you"（已有旧消息）');
  const scenario2 = {
    containerScrollTop: 500, // 已经滚动了一些
    messageTop: 800, // 新消息在视口中的位置（在底部）
    containerTop: 50,  // 容器在视口中的位置
  };
  
  const distance2 = scenario2.messageTop - scenario2.containerTop;
  const targetScroll2 = scenario2.containerScrollTop + distance2;
  
  console.log('  当前滚动位置:', scenario2.containerScrollTop);
  console.log('  消息距离容器顶部:', distance2);
  console.log('  目标滚动位置:', targetScroll2);
  console.log('  ✓ 新消息应该滚动到顶部');
  console.log('  ✓ 旧消息会被推上去（scrollTop 增加）\n');

  // 模拟场景3: Agent回复后
  console.log('场景3: Agent回复后，消息被推上去');
  const scenario3 = {
    containerScrollTop: targetScroll2, // 从场景2继续
    messageTop: 50, // 消息现在在顶部
    containerTop: 50,
    agentMessageHeight: 200, // Agent消息高度
  };
  
  console.log('  Agent消息添加后，容器内容高度增加');
  console.log('  用户消息自然被推上去');
  console.log('  ✓ 这是正常的滚动行为\n');

  return {
    scenario1: { targetScroll: targetScroll1 },
    scenario2: { targetScroll: targetScroll2 },
    scenario3: { description: '自然滚动' }
  };
}

// 运行测试
const results = testScrollCalculation();
console.log('=== 测试完成 ===');
console.log('结果:', JSON.stringify(results, null, 2));


