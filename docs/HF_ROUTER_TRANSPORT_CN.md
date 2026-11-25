# HF Router 传输层（2026-11-25）

## 背景

Owner 实测：huggingface_hub 2.4.0 旧 Provider Mapping 为空，SDK
在准备请求阶段拒绝历史 DeepInfra 路由；Router 全量目录却列出模型与
live Provider。HTTPX 直接调用 Router 已返回 HTTP 200、DeepInfra、
严格 JSON Schema 与完整六维响应。六维响应因 source/target 引文错位
被严格校验拒绝；这是质量层问题，不是传输问题。R60 冻结
SafeDiagnosticClient 已有确定性引文归位机制，不复制或放宽校验。
上述真实响应未通过最终 Judge 校验，不能登记为完整评分 PASS。

## 使用

安装可选依赖：`pip install -e '.[hf-router]'`。
在已明确授权的数据和费用范围内使用：

```python
import os
from storyforge_inference.hf_router import HFRouterClient

with HFRouterClient(
    token=os.environ["HF_TOKEN"],
    model="deepseek-ai/DeepSeek-V4.1-Flash-1017",
    provider="deepinfra",
    bill_to="adradar",
    response_model="deepseek/deepseek-v4.1-flash-1017",
    response_provider="DeepInfra",
) as client:
    route = client.preflight()  # 只 GET，不推理；应在 attempt marker 之前
    # 正式调用前由上层检查授权、写 create-only attempt marker。
    # client.chat_completion(...) 与冻结 judge_one 客户端接口兼容。
```

显式固定请求 model:provider 和已观察到的响应身份；不自动切换。
目录价格和 live 不保证计费授权或真实可用性。组织账单需 Owner 核对。
每次 chat_completion 最多一次 POST，无应用层重试/重定向。
上层负责私有材料审查、单次执行锁、费用授权、不可重复 attempt、
安全保存结果。不要将 raw HTTP、异常原文、token、私有模型输出写入日志。
client.info 仅提供阶段、状态码、异常类、结束原因及字符数。

R60 冻结 archive 的 Gold48 Judge 不在 main，不能直接重跑其 240 项
runner。后续 Gold3 入口注入本客户端，并复用冻结
SafeDiagnosticClient 的引文归位、原始响应私有留存和审计；其额外
reasoning_effort=none 参数经 Router 路线尚未实测，故本模块不默认添加。
已观察真实请求未设置该参数。调用者须显式选择并验证。现有评分标准
不变。不得因此启动 R61 或重评 R60。

离线测试：`pytest -q tests/test_hf_router.py`。Mock HTTP 不产生费用。
