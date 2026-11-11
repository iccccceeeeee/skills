# Image 2.6 GIF API 参考

默认模型为 `gpt-image-2.6-flare`。用户指定 Sunburst 时使用 `--model gpt-image-2.6-sunburst`。

## 参数

`generate` 每次创建一段 GIF，支持纯文本或文本加参考图。脚本发送 `output_format: "gif"`、`size: "auto"` 和 `n: 1`，画质默认为 `auto`。帧数、帧间隔和尺寸由模型决定。

参考图可用 `--image-file` 指定本地文件，也可用 `--image-url` 传 HTTPS 链接或 `data:image/...;base64,...`。两种参数均可重复，总计最多八张。脚本将参考图放入 `image_urls`，本地文件会转换为 data URL。服务根据有无参考图选择生成方式。

```bash
python3 scripts/generate_image26_gif.py generate \
  --prompt "一盏纸灯笼随风轻摆，无缝循环" \
  --image-file ./lantern.png \
  --async --wait --download-dir ./out/images --json
```

纯文生 GIF 标准价为每个成功结果 ¥0.0833。Flare 文生 GIF 触发备用通道时每个成功结果 ¥0.30。参考图生成 GIF 按实际用量结算。下载时保留原始 GIF 字节。

## 接口

默认地址为 `https://jp.icodeeasy.cc`，可以通过 `--base-url` 指定其他 iCodeEasy API 地址。

- 创建 GIF 使用 `POST /v1/images/generations`。
- 查询任务使用 `GET /v1/images/tasks/{task_id}`。

`--async` 仅提交任务，加上 `--wait` 后会等待结果。默认同步模式使用 `?sync=1`，同时处理接口返回异步任务的情况。

## 恢复结果

```bash
python3 scripts/generate_image26_gif.py poll <task_id> \
  --wait --download-dir ./out/images --json
```

轮询失败或下载失败时，保留任务 ID 和已有结果，继续恢复同一个任务。重新生成会创建新的付费任务。

## 离线检查

```bash
python3 scripts/generate_image26_gif.py generate \
  --prompt "一盏纸灯笼轻轻摇摆，无缝循环" --dry-run --json
```

`--dry-run` 只检查参数和请求体。错误响应以接口返回的具体信息为准。任务已创建后以任务查询结果判断生成状态。
