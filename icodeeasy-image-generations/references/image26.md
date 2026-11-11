# Image 2.6 静态图片 API 参考

默认模型为 `gpt-image-2.6-flare`。用户明确指定 Sunburst 时使用 `gpt-image-2.6-sunburst`。

## 参数

每个任务生成一张 PNG，参考图最多八张。分辨率可选 `1k`、`2k` 或 `4k`，背景使用 `auto`。实际像素以返回图片为准。

画质可选 `auto`、`low`、`medium`、`high`，默认 `auto`。Flare 和 Sunburst 均按成功结果收费。1K 每张 ¥0.0833，2K 每张 ¥0.294，4K 每张 ¥0.392。

支持的比例为 `auto`、`1:1`、`3:2`、`2:3`、`16:9`、`9:16`、`4:3`、`3:4`、`4:5`、`5:4`。

用 `--resolution` 选择分辨率，脚本发送 `image_size`，默认为 `"1K"`。需要明确比例时使用 `--aspect-ratio`，脚本发送 `aspect_ratio`。

参考图使用 `--image-file` 或 `--image-url`，都可以重复。脚本将本地文件编码后放入 `image_urls`。2K 和 4K 的参考图仅支持 PNG、JPEG 和 WebP。

## 接口

默认地址为 `https://jp.icodeeasy.cc`，可以通过 `--base-url` 指定其他 iCodeEasy API 地址。

- 文生图使用 `POST /v1/images/generations`。
- 图片编辑使用 `POST /v1/images/edits`，至少提供一张参考图。
- 查询任务使用 `GET /v1/images/tasks/{task_id}`。

`--async` 仅提交任务；加上 `--wait` 后会等待结果。默认同步模式使用 `?sync=1`，同时处理接口返回异步任务的情况。

## 恢复结果

```bash
python3 scripts/generate_image26.py poll <task_id> \
  --wait --download-dir ./out/images --json
```

轮询失败或下载失败时，保留任务 ID 与已有结果，继续恢复同一个任务。重新生成会创建新的付费任务。

## 离线检查

```bash
python3 scripts/generate_image26.py generate \
  --prompt "浅色木桌上的陶瓷咖啡杯" --dry-run --json
```

`--dry-run` 只检查参数和请求体。

错误响应以接口返回的具体信息为准。认证失败时检查密钥环境变量；任务已创建后以任务查询结果判断生成状态。
