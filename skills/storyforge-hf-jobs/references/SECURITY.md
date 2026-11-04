# 安全边界

## 文件与 Volume

- 输入使用 `InputManager.open_verified`；验证 regular file、no-follow、大小、打开后 descriptor identity 和 SHA256。
- 不把 HF RO mount 的 mode bits、UID、link count 当成隐私或完整性证明。
- 输出目录必须预先存在；先执行真实能力探针。
- SAFE 目标必须 create-only；不能覆盖已存在文件。
- 原子发布只允许经过 Runtime 验证的 no-replace 机制；不支持时 fail closed。
- 清理仅能删除本次创建且 inode identity 匹配的临时对象。

## 私有数据

公开 GitHub 只能保存代码、合成测试和经审查的聚合证据。PRIVATE 原文、Gold、R50、R59 Prompt、逐案 ID、交叉表、私有哈希、模型原始输出和凭据均留在受控私有存储。

## CPU/GPU

CPU Profile 必须检查平台 Accelerator、CUDA 可见性、NVIDIA 设备节点及 GPU 相关执行路径。单独设置 `CUDA_VISIBLE_DEVICES=""` 不构成完整保证。未知状态 fail closed。

Runtime 本身不提交 Job、不下载模型、不导入训练框架、不调用 CUDA、不执行推理或训练。GPU 和训练必须有独立 Owner 明确授权。
