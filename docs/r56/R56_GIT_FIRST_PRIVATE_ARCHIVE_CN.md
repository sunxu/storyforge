# R56 私有审核档案：Git-first 安全边界

## 已提交与未提交

- **可直接提交**：CPU-only Python/Bash 源码、合成测试、README、脱敏计数、校验规则和**不指向私有个案的**源码 SHA256 清单。
- **不可明文提交**：Gold 目标、冻结对话、原始小说、候选 ID、来源消息 ID、详细 Reviewer 决定、跨世界私有证据和 R50 密封题。私有 GitHub 仓库与 Git LFS **不等于**盲审隔离；删除后 Git 提交历史可能仍保留内容。
- **含内嵌私有常量的 Stage3–5 代码**：需要先参数化并通过隐私扫描，再逐批提交。
- **R50**：继续单独密封，不归档到 R56，即使加密也不混入本仓库。

## 用 age 对私有审核 ZIP 加密

首次使用请在 **Owner Mac** 自行生成身份密钥，并始终保存在 Git 仓库以外：

```bash
brew install age
mkdir -p "$HOME/.config/storyforge"
chmod 700 "$HOME/.config/storyforge"
age-keygen -o "$HOME/.config/storyforge/r56-age-identity.txt"
chmod 600 "$HOME/.config/storyforge/r56-age-identity.txt"
age-keygen -y "$HOME/.config/storyforge/r56-age-identity.txt"
```

最后一行得到一个公开的 `age1...` 接收方公钥；**不需要上传私钥**。随后：

```bash
cd "$HOME/workspace/storyforge"
bash tools/r56/scripts/r56_encrypt_private_audit.sh \
  --repo "$PWD" \
  --source "$HOME/Downloads/StoryForge_R56_Stage5_World11_ReviewAndVerifier_PRIVATE_20261022.zip" \
  --recipient 'age1...你的公钥...' \
  --name stage5-review-20261022
```

本脚本拒绝 R50、拒绝明文 ZIP 放在 Git 工作树内、拒绝覆盖已存在的加密包；只写出 `.zip.age`，**不会自动 git add、提交或上传**。运行后自己用保存在仓库外的私钥解密到临时目录，确认可读、CRC 通过再删掉临时解密件。

```bash
age -d -i "$HOME/.config/storyforge/r56-age-identity.txt" \
  -o "$HOME/.local/share/storyforge/r56/private-verify-stage5.zip" \
  audits/r56/encrypted/stage5-review-20261022.zip.age
unzip -tq "$HOME/.local/share/storyforge/r56/private-verify-stage5.zip"
```

确认之后才可明确选择 `git add audits/r56/encrypted/stage5-review-20261022.zip.age`，在单独的受限权限 Git 仓库归档更好。如果必须存主仓库，确保后续 Reviewer 不获得解密密钥。切勿提交 `r56-age-identity.txt` 或临时解密 ZIP。

## 资格门禁

全部原 R56 24 条仍为 HOLD，KSG 18 条中 9 条内容筛出、9 条内容 HOLD；独立世界认证尚未建立，正式 Held-out 准入 0。此前 CPU 源码单元测试通过不等于批准训练、运行 GPU、读取 R50 或晋升 R54。
