# Image 2.6 GIF API 参考

默认模型为 `gpt-image-2.6-flare`。用户指定 Sunburst 时使用 `--model gpt-image-2.6-sunburst`。

## 参数

`generate` 每次创建一段 GIF。脚本默认发送 `output_format: "gif"`、`n: 1` 和 `quality: "auto"`。

- `--frame-count` 为 2–16，默认 9。
- `--frame-duration-ms` 至少 20，采用 10 ms 的整数倍，默认 200。动画总时长为帧数乘帧间隔。
- `--frame-size` 为 `auto` 或 `WIDTHxHEIGHT`，默认 `auto`，对应单帧 512×512。明确尺寸须为 16 的倍数。

脚本将帧数、帧间隔和单帧尺寸分别发送为 `frame_count`、`frame_duration_ms` 和 `size`。GIF 使用单帧像素尺寸，仅支持文字生成。

帧会组合成生成画布，尺寸与帧数需要一起校验。2–8 帧使用 4×2 布局，9 帧使用 3×3，10–12 帧使用 4×3，13–16 帧使用 4×4，布局可转置。整张画布每边最多 3840，最多 8,294,400 像素，最大宽高比为 3:1。默认 512×512 适用于所有帧数。

例如四秒动画可使用 10 帧、每帧 400 ms。

```bash
python3 scripts/generate_image.py generate \
  --prompt "一盏纸灯笼随风轻摆，无缝循环" \
  --frame-count 10 --frame-duration-ms 400 \
  --async --wait --download-dir ./out/images --json
```

费用按完整任务的实际用量结算，下载时保留原始 GIF 字节。

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
