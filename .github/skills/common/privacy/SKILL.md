---
name: privacy
description: "プライバシーの実装：PII保存禁止・匿名/不透明なユーザーID・ログの匿名化・抽象化されたエラーメッセージ・必須のデータ削除フロー。ユーザーデータの保存・ロギング・削除機能の実装時に使用する。"
applyTo: ["app/features/auth/**/*.py", "app/features/admin/**/*.py"]
---

# Privacy Skill

---

## ストレージ

- キャッシュ（メモリ・Redis 等）に PII を保存しない
- ユーザー識別子は不透明な UUID 等のオペーク ID
- データ削除フローを必ず実装する
- キャッシュに PII が残らないよう TTL とキャッシュ制御を設定

```python
# NG
cache.set(f"user:{username}", data)

# OK
cache.set(f"user:{user_id}", data)
```

---

## ロギング

- ログに PII（氏名・メール・電話番号等）を含めない
- エラーメッセージは抽象化し、内部構造・スタックトレースを返さない
- ログに含めてよいのは不透明 ID（UUID）・操作種別・タイムスタンプのみ

```python
import structlog

logger = structlog.get_logger()

# NG
logger.info("ログイン", email=user.email)

# OK
logger.info("ログイン", user_id=str(user.id), action="login")
```

---

## エラーレスポンス

- 内部エラーメッセージ・ファイルパス・クラス名を返さない
- クライアントには抽象的なエラーコードのみ

```python
from fastapi.responses import JSONResponse

# NG
return JSONResponse(
    status_code=500,
    content={"message": str(exc), "traceback": traceback.format_exc()},
)

# OK
return JSONResponse(
    status_code=500,
    content={"code": "INTERNAL_ERROR"},
)
```

---

## 境界条件

- PII が `None` の場合はデフォルト値で補完せず明示的に処理
- 削除済みユーザーのデータへのアクセスを拒否する
