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

- `model`: currently `gpt-image-2`.
- `prompt`: image prompt, Chinese or English.

Optional:

- `n`: image count, default `1`.
- `resolution`: `1k` or `2k`, default `1k`.
- `quality`: `low`, `medium`, `high`, or `auto`, default billing is `medium`.
- `image_urls`: up to 16 reference images. Each item must be an `https://` URL or a `data:image/...;base64,...` data URL.

`quality` controls billing tier, not image quality semantics. Billing is per image: low ¥0.10, medium/auto ¥0.20, high ¥0.40.

## Sync and async

Default sync response, HTTP 200:

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
