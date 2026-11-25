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

## Gold3 接入离线验收

使用独立 worktree；从固定 R60 归档提取原评审包（不运行旧批处理入口）。
在仓库根目录执行：

```bash
git fetch origin archive/r60-final-20261122
ARCHIVE=$(mktemp -d)
git archive 15462b8779401833a5014846bc57318dd6bc1b1c \
  src/storyforge_gold_quality src/storyforge_dataset | tar -xf - -C "$ARCHIVE"
STORYFORGE_GOLD3_ARCHIVE_TEST=1 PYTHONPATH="$ARCHIVE/src:$PWD/src:$PWD" \
  python -m pytest -q tests/test_hf_router.py tests/test_gold3_router_integration.py
```

测试只用合成材料及 MockTransport，复播已观察的六维响应并检验
原评分不变、引文归位、虚构引文 HOLD、重复执行及 attempt 创建竞争。
不发真实 API。普通 main 测试环境没有冻结归档时跳过这四项集成测试；
专门验收必须显式启用，缺少归档则失败而非跳过。
Gold3 实际执行沿用原私有材料与输出目录，默认离线。
旧 attempt 不删除。R61、训练及正式准入均保持禁止。

## C3 输出预算补偿

C3 首次真实请求 HTTP 200、finish_reason=length、content=null，未取得评分。
Gold3 默认 4096 输出 tokens（冻结 judge 的上限）；不改评分器及 R60 归档。
保留 2048 作为显式历史预算选项。Router 诊断仅增加白名单数值 usage，
不记录推理正文。4096 不保证完成，且可能增加费用。

仅 C3 可通过 --compensate-length-hold --max-tokens 4096 单次补偿。
必须同时提供原三项 Owner 授权，核对原 attempt、diagnostic 与材料/路由，
且原请求为已消耗的 HTTP 200 length HOLD、无原始评分或回复。
原文件不动；新文件使用 .compensation1 后缀，create-only，绑定旧记录哈希。
失败后不再自动重试，不扩展 C1/C2，不启动 R61。

## C3 第二次截断后的最终补偿

4096 输出预算耗尽，4092 reasoning tokens、content=null。Owner 要求不限定
Token 用量：默认省略实际 HTTP 请求的 max_tokens 字段，由 Provider 决定，
不承诺 Provider 无上限。显式正整数仍可用于其他单次评审。
冻结 judge 内部 4096 仅用于其原有参数校验，适配器替换实际传输预算，
不修改归档、评分规则、Prompt 或引文校验。Gold3 HTTP 超时为 900 秒。
C3 默认预算补偿必须验证原始及 compensation1 的 length HOLD、哈希链、
无可恢复响应/评分；新记录仅 compensation2，create-only，禁止自动重试。
使用 --compensate-length-hold 且不传 --max-tokens，原三项授权仍必须提供。

## C1/C2 历史 SDK HOLD 补偿

Owner 单独授权 C1、C2 各一次补偿，历史调用和计费结果仍未知。仅允许这两个 case 使用 `--compensate-legacy-hold`，不传 `--max-tokens`，保留三项 Owner 授权。核对旧 attempt 与输入哈希，保留可选旧诊断；有旧响应或评分则拒绝。新记录使用 `.compensation1`，独占创建，关联旧记录哈希，不自动重试。不改变 C3、冻结评分器及准入状态。
