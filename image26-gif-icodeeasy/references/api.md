# Image 2.6 GIF API 参考

默认模型为 `gpt-image-2.6-flare`。用户指定 Sunburst 时使用 `--model gpt-image-2.6-sunburst`。

## 参数

`generate` 每次从文本创建一段 GIF。脚本发送 `output_format: "gif"`、`size: "auto"` 和 `n: 1`，画质默认为 `auto`。帧数、帧间隔和尺寸由模型决定。

```bash
python3 scripts/generate_image.py generate \
  --prompt "一盏纸灯笼随风轻摆，无缝循环" \
  --async --wait --download-dir ./out/images --json
```

按成功结果收费，每段 ¥0.0833。下载时保留原始 GIF 字节。

## 接口

默认地址为 `https://jp.icodeeasy.cc`，可以通过 `--base-url` 指定其他 iCodeEasy API 地址。

- 创建 GIF 使用 `POST /v1/images/generations`。
- 查询任务使用 `GET /v1/images/tasks/{task_id}`。

`--async` 仅提交任务，加上 `--wait` 后会等待结果。默认同步模式使用 `?sync=1`，同时处理接口返回异步任务的情况。

## 恢复结果

```bash
python3 scripts/generate_image.py poll <task_id> \
  --wait --download-dir ./out/images --json
```

轮询失败或下载失败时，保留任务 ID 和已有结果，继续恢复同一个任务。重新生成会创建新的付费任务。

## 离线检查

```bash
python3 scripts/generate_image.py generate \
  --prompt "一盏纸灯笼轻轻摇摆，无缝循环" --dry-run --json
```

`--dry-run` 只检查参数和请求体。错误响应以接口返回的具体信息为准。任务已创建后以任务查询结果判断生成状态。
