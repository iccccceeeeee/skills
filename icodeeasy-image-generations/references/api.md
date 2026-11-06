# iCodeEasy Images API Reference

Use these endpoints:

```text
POST https://jp.icodeeasy.cc/v1/images/generations
POST https://jp.icodeeasy.cc/v1/images/edits
```

Use `generations` for text-to-image. Use `edits` when the user explicitly wants to edit an existing image. In both JSON forms, send reference images in `image_urls`.

Skill policy: do not send `size`, even though the upstream API supports it. Let the API apply its default sizing behavior.

## Authentication

Headers:

```text
Authorization: Bearer <api key>
Content-Type: application/json
```

The local script reads the key from `OPENAI_API_KEY`, then `ANTHROPIC_AUTH_TOKEN`.

## Request JSON

Required:

- `model`: defaults to `gpt-image-2`. The script also accepts the `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`, `gpt-image-2.6-flare`, and `gpt-image-2.6-sunburst` static image variants.
- `prompt`: image prompt, Chinese or English.

Optional:

- `n`: use `1` per task; submit separate tasks for multiple images.
- `image_size`: `1K`, `2K`, or `4K` for Image 2 and 2.5. Image 2.6 supports `1K` only. The script’s `--resolution` option sets this field and defaults to `1K`.
- `quality`: `low`, `medium`, `high`, or `auto`. Defaults to `medium` for Image 2 and `auto` for Image 2.5 and 2.6.
- `image_urls`: up to 8 reference images. Each item must be an `https://` URL or a `data:image/...;base64,...` data URL.

Billing follows the actual completed task charge. Quality does not select an additional price tier for Image 2. Image 2.6 costs ¥0.0833 per successful result.

## Sync and async

Explicit synchronous requests use `?sync=1` and return HTTP 200. The script also handles an asynchronous task response by polling the same task.

```json
{
  "id": "3e0c77bb-9cbd-4c44-9549-bff1b4060623",
  "created": 1781599773,
  "data": [
    {
      "url": "https://api.icodeeasy.cc/v1/images/files/.../image.png"
    }
  ]
}
```

Async submit:

```text
POST https://jp.icodeeasy.cc/v1/images/generations?async=1
POST https://jp.icodeeasy.cc/v1/images/edits?async=1
```

HTTP 202 response:

```json
{ "status": "pending", "task_id": "d142c93a-de26-40c9-be62-0de840d10960" }
```

Poll:

```text
GET https://jp.icodeeasy.cc/v1/images/tasks/{task_id}
```

Completed response includes `result_url`.

## Link handling

The API returns URL links only. It does not support `response_format: b64_json`. Result URLs are long-lived and do not require an API key, so treat them as sensitive bearer links.
