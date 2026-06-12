# استخدام نماذج OpenCode Zen المجانية في مشاريعك

## المزود: OpenCode Zen

**Base URL:** `https://opencode.ai/zen/v1`
**API Key:** `public` (ثابتة — لا تحتاج حساب ولا تسجيل)

الاتصال يتم مباشرة عبر واجهة OpenAI-compatible. أي مكتبة تدعم OpenAI API تستطيع استخدام هذه النماذج.

---

## جلب قائمة النماذج المجانية آلياً

بدلاً من حفظ أسماء النماذج يدوياً، اسأل السيرفر مباشرة:

```python
import httpx

r = httpx.get("https://opencode.ai/zen/v1/models", timeout=10)
all_models = r.json()["data"]
free_models = [m["id"] for m in all_models if "free" in m["id"].lower()]
print(free_models)
# مثال: ['deepseek-v4-flash-free', 'mimo-v2.5-free', 'qwen3.6-plus-free', ...]
```

```bash
curl https://opencode.ai/zen/v1/models | jq '.data[].id'
```

> نصيحة: خزّن النتائج مؤقتاً لمدة ساعة (cache) لتجنب الطلبات المتكررة.

---

## النماذج المجانية (حسب آخر فحص)

| النموذج | الحالة |
|---------|--------|
| `deepseek-v4-flash-free` | يعمل — سريع، دعم أدوات (tool calling)، استدلال |
| `mimo-v2.5-free` | يعمل |
| `minimax-m3-free` | يعمل — مع تفكير داخلي (thinking) |
| `nemotron-3-super-free` | يعمل — سريع |
| `qwen3.6-plus-free` | ❌ انتهت الفترة المجانية |

> النماذج تتغير باستمرار. استخدم `/v1/models` للحصول على القائمة المحدثة.

---

## أمثلة استخدام

### 1. Python مع httpx

```python
import httpx

response = httpx.post(
    "https://opencode.ai/zen/v1/chat/completions",
    headers={
        "Authorization": "Bearer public",
        "Content-Type": "application/json"
    },
    json={
        "model": "deepseek-v4-flash-free",
        "messages": [{"role": "user", "content": "مرحباً"}],
        "max_tokens": 1024
    }
)

print(response.json()["choices"][0]["message"]["content"])
```

### 2. Python مع OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://opencode.ai/zen/v1",
    api_key="public"
)

response = client.chat.completions.create(
    model="deepseek-v4-flash-free",
    messages=[{"role": "user", "content": "Hello in 3 words"}]
)

print(response.choices[0].message.content)
```

### 3. cURL

```bash
curl https://opencode.ai/zen/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer public" \
  -d '{
    "model": "deepseek-v4-flash-free",
    "messages": [{"role": "user", "content": "Say hello in 3 words"}],
    "max_tokens": 50
  }'
```

### 4. JavaScript (Fetch)

```javascript
const response = await fetch("https://opencode.ai/zen/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer public"
  },
  body: JSON.stringify({
    model: "deepseek-v4-flash-free",
    messages: [{ role: "user", content: "Say hello in 3 words" }],
    max_tokens: 50
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

### 5. JavaScript مع Vercel AI SDK

```javascript
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

const { text } = await generateText({
  model: openai("deepseek-v4-flash-free", {
    baseURL: "https://opencode.ai/zen/v1",
  }),
  apiKey: "public",
  messages: [{ role: "user", content: "Say hello in 3 words" }],
});
```

### 6. Streaming (Python httpx)

```python
import httpx
import json

with httpx.stream(
    "POST",
    "https://opencode.ai/zen/v1/chat/completions",
    headers={
        "Authorization": "Bearer public",
        "Content-Type": "application/json"
    },
    json={
        "model": "deepseek-v4-flash-free",
        "messages": [{"role": "user", "content": "Write a poem"}],
        "max_tokens": 1024,
        "stream": True
    },
    timeout=120
) as resp:
    for line in resp.iter_lines():
        if line and line.startswith("data: ") and line != "data: [DONE]":
            chunk = json.loads(line[6:])
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                print(delta["content"], end="", flush=True)
            if delta.get("reasoning_content"):
                print(f"[تفكير: {delta['reasoning_content']}]", end="", flush=True)
```

---

## دعم الأدوات (Tool Calling / Function Calling)

النماذج تدعم tool calling بنفس صيغة OpenAI:

```python
import httpx, json

response = httpx.post(
    "https://opencode.ai/zen/v1/chat/completions",
    headers={"Authorization": "Bearer public", "Content-Type": "application/json"},
    json={
        "model": "deepseek-v4-flash-free",
        "messages": [{"role": "user", "content": "What files are here?"}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List directory contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path"}
                    },
                    "required": ["path"]
                }
            }
        }],
        "tool_choice": "auto"
    }
)

message = response.json()["choices"][0]["message"]
if message.get("tool_calls"):
    for tc in message["tool_calls"]:
        print(f"Tool: {tc['function']['name']}")
        print(f"Args: {tc['function']['arguments']}")
```

---

## الحدود والقيود

- **Rate Limit:** قد تحصل على `429 Too Many Requests` عند الاستخدام المكثف. الحل: إعادة المحاولة بعد `2^n` ثانية أو التبديل لنموذج مجاني آخر
- **طول السياق:** يختلف حسب النموذج (عادة 32K-128K رمز)
- **لا يوجد ضمان للاستمرارية:** هذه نماذج مجانية وقد تتوقف أو تتغير بدون إشعار — استخدم `/v1/models` باستمرار
- **عدد الطلبات:** محدود — مناسب للاستخدام الشخصي والتجريب، ليس لتطبيقات الإنتاج

---

## استكشاف الأخطاء

| الخطأ | السبب | الحل |
|-------|-------|------|
| `401 Missing API key` | لم ترسل `Authorization: Bearer public` | أضف الهيدر |
| `429 Provider returned error` | تجاوزت الحد المسموح | انتظر 5 ثوان وأعد المحاولة، أو استخدم نموذجاً آخر |
| `400 Messages with role 'tool'...` | ترتيب رسائل غير صحيح | تأكد أن رسالة الـ tool تأتي بعد رسالة assistant تحتوي tool_calls |
| `ModelError: Free promotion has ended` | النموذج لم يعد متاحاً مجاناً | استخدم `/v1/models` لتعثر على نموذج مجاني آخر |

---

## بنية الـ API

السيرفر متوافق تماماً مع **OpenAI Chat Completions API**:

```
GET  https://opencode.ai/zen/v1/models              # قائمة النماذج (بدون Auth)
POST https://opencode.ai/zen/v1/chat/completions     # محادثة (مع Auth: Bearer public)
```

`GET /models` لا يحتاج أي توثيق. `POST /chat/completions` يحتاج `Authorization: Bearer public`.
