# Image 2.6 API 参考

默认模型为 `gpt-image-2.6-flare`。用户明确指定 Sunburst 时使用 `gpt-image-2.6-sunburst`。

## 参数

PNG 支持 `1k`、`2k`、`4k` 请求档位，背景使用 `auto`。实际像素以返回图片为准。PNG 编辑最多使用八张参考图。

画质可选 `auto`、`low`、`medium`、`high`。按实际任务用量结算，费用随请求变化。

PNG 支持的比例为 `auto`、`1:1`、`3:2`、`2:3`、`16:9`、`9:16`、`4:3`、`3:4`、`4:5`、`5:4`。

### GIF 动图

- 使用 `generate --format gif`，每个任务生成一段动画。
- `--frame-count` 为 2–16，默认 9。
- `--frame-duration-ms` 至少 20，采用 10 ms 的整数倍，默认 200。动画总时长为帧数乘帧间隔。
- `--frame-size` 为 `auto` 或 `WIDTHxHEIGHT`，默认 `auto`，对应每帧 512×512。明确尺寸须为 16 的倍数。
- GIF 使用帧尺寸，省略 `--resolution` 与 `--aspect-ratio`。
- GIF 仅支持文生图。参考图、蒙版和编辑请求不适用。

帧会组合成生成画布，尺寸与帧数需要一起校验。2–8 帧使用 4×2 布局，9 帧使用 3×3，10–12 帧使用 4×3，13–16 帧使用 4×4；布局可转置。整张画布每边最多 3840，最多 8,294,400 像素，最大宽高比为 3:1。默认 512×512 适用于所有帧数。

例如四秒动画可使用 10 帧、每帧 400 ms。

```bash
python3 scripts/generate_image.py generate \
  --prompt "一盏纸灯笼随风轻摆，无缝循环" --format gif \
  --frame-count 10 --frame-duration-ms 400 \
  --async --wait --download-dir ./out/images --json
```

生成费用按完整任务的实际用量结算，保留返回 GIF 的原始字节。

PNG 使用 `--resolution` 设置分辨率，并发送接口的 `image_size` 字段。需要明确 PNG 比例时使用 `--aspect-ratio`。GIF 发送 `output_format`、`frame_count`、`frame_duration_ms` 和单帧像素 `size`。

参考图使用 `--image-file` 或 `--image-url`，都可以重复。脚本将本地文件编码后放入 `image_urls`。

## 接口

默认地址为 `https://jp.icodeeasy.cc`，可以通过 `--base-url` 指定其他 iCodeEasy API 地址。

- 文生图使用 `POST /v1/images/generations`。
- PNG 编辑使用 `POST /v1/images/edits`，至少提供一张参考图。GIF 使用生成端点。
- 查询任务使用 `GET /v1/images/tasks/{task_id}`。

`--async` 仅提交任务；加上 `--wait` 后会等待结果。默认同步模式使用 `?sync=1`，同时处理接口返回异步任务的情况。

## 恢复结果

```bash
python3 scripts/generate_image.py poll <task_id> \
  --wait --download-dir ./out/images --json
```

轮询失败或下载失败时，保留任务 ID 与已有结果，继续恢复同一个任务。重新生成会创建新的付费任务。

## 离线检查

```bash
python3 scripts/generate_image.py generate \
  --prompt "浅色木桌上的陶瓷咖啡杯" --dry-run --json
```

`--dry-run` 只检查参数和请求体。

错误响应以接口返回的具体信息为准。认证失败时检查密钥环境变量；任务已创建后以任务查询结果判断生成状态。
