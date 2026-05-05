---
description: "React 19 + MUI v9 + TanStack Query v5 のフロントエンド実装規約。コンポーネント設計・hooks・API 呼び出し・状態管理・MUI パターンをカバーする。"
applyTo: "frontend/src/**/*.{ts,tsx}"
---

# Frontend TypeScript Instructions

> **SSOT**: このファイルがフロントエンド実装の唯一の正とする。
> **根拠**: `frontend/src/` の実装パターン・MUI v9 / TanStack Query v5 の実績コードベース

---

## 概要

React 19 + TypeScript + MUI v9 + TanStack Query v5 + react-i18next v15（4ロケール）を使用する。
60 画面以上・8 名並行開発のため、統一パターンで可読性・保守性を担保する。

---

## L2 ルール（このドメイン固有）

| レベル | ルール                                                                | 違反時の動作                           |
| ------ | --------------------------------------------------------------------- | -------------------------------------- |
| L2     | `any` 型を使用する（L1 と同等）                                       | 即停止・報告                           |
| L2     | MUI deprecated API を使用する（例: `primaryTypographyProps`）         | `[L2 警告]` + 代替 API を提示          |
| L2     | `useQuery` / `useMutation` を直接ページ内に複数バラ定義する（5 件超） | `[L2 警告]` + hooks への切り出しを提案 |
| L2     | `queryKey` を文字列リテラルで直接記述する（定数化せず）               | `[L2 警告]` + 定数化を提示             |
| L2     | コンポーネントに副作用（API 呼び出し）と表示ロジックを混在させる      | `[L2 警告]` + 分離案を提示             |
| L2     | MUI `sx` に固定 pixel 値を直接記述する（テーマトークン未使用）        | `[L2 警告]`                            |

---

## ファイル構造

```
frontend/src/
  api/
    client.ts          # Axios インスタンス（共通ベース URL・Cookie 送信設定）
    endpoints/
      types.ts         # 全 API リクエスト/レスポンス型（SSOT）
      apis.ts          # API 呼び出し関数（ドメイン別オブジェクト）
      index.ts         # re-export
  contexts/            # React Context（ToastContext など）
  hooks/               # 共通カスタム hooks（useAuth, useToast など）
  i18n/                # i18next 設定・ロケールファイル
  layouts/             # ページレイアウト（MainLayout など）
  pages/               # SCR-NNN_PageName.tsx（1 画面 1 ファイル）
  components/          # 再利用コンポーネント（機能横断）
  App.tsx              # ルーティング定義（lazy import 必須）
```

---

## ページコンポーネント規約

### 命名

- `SCR{NNN}_{FeatureName}Page.tsx`（例: `SCR023_RegWatchUrlPage.tsx`）
- 1 ファイル 1 デフォルトエクスポート・複数責務禁止

### 構造テンプレート

```tsx
/**
 * {機能名}ページ（SCR{NNN}）。
 * {目的の 1 行説明}。{権限の説明}。
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useToast } from "../contexts/ToastContext";
import { someApi } from "../api/endpoints";
import type { SomeType, SomeCreateRequest } from "../api/endpoints";

// ページ内 query key（定数化でタイポ防止）
const QUERY_KEY = ["feature-name"] as const;

export default function FeaturePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();

  // データ取得
  const { data, isLoading, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => someApi.getAll(),
    select: (res) => res.data,
  });

  // 作成ミューテーション
  const createMutation = useMutation({
    mutationFn: (payload: SomeCreateRequest) => someApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      showSuccess(t("feature.success_create"));
    },
    onError: () => showError(t("feature.error_create")),
  });

  if (error) return <Alert severity="error">{t("common.error_generic")}</Alert>;

  return <Box>{isLoading ? <Skeleton /> : /* 本体 */ null}</Box>;
}
```

---

## API 層規約

### types.ts — 型定義

```typescript
// NG: 個々のファイルで型を定義する
interface MyType {
  id: string;
} // 各ページに散在させない

// OK: frontend/src/api/endpoints/types.ts に集約
export interface MyType {
  id: string;
  name: string;
  // snake_case（バックエンド Pydantic と揃える）
  created_at: string;
}

export interface MyCreateRequest {
  name: string;
}
```

### apis.ts — API 関数

```typescript
// ドメイン別オブジェクトで CRUD を集約
export const myFeatureApi = {
  getAll: (cursor?: string | null, limit?: number) =>
    apiClient.get<CursorPage<MyType>>("/my-feature", {
      params: { cursor, limit },
    }),
  getById: (id: string) => apiClient.get<MyType>(`/my-feature/${id}`),
  create: (data: MyCreateRequest) =>
    apiClient.post<MyType>("/my-feature", data),
  update: (id: string, data: MyUpdateRequest) =>
    apiClient.patch<MyType>(`/my-feature/${id}`, data),
  delete: (id: string) => apiClient.delete(`/my-feature/${id}`),
};
```

---

## TanStack Query v5 パターン

### queryKey 設計

```typescript
// NG: 文字列リテラルをバラバラに記述
useQuery({ queryKey: ['my-feature'] });
queryClient.invalidateQueries({ queryKey: ['my-feature'] });  // タイポリスク

// OK: ページ先頭で定数化
const QUERY_KEY = ['my-feature'] as const;
const DETAIL_QUERY_KEY = (id: string) => ['my-feature', id] as const;

useQuery({ queryKey: QUERY_KEY, ... });
queryClient.invalidateQueries({ queryKey: QUERY_KEY });
```

### select でレスポンス変換

```typescript
// axios レスポンスの .data を select で取り出す
const { data } = useQuery({
  queryKey: QUERY_KEY,
  queryFn: () => someApi.getAll(),
  select: (res) => res.data, // AxiosResponse<T> → T
});
```

### useMutation パターン

```typescript
const mutation = useMutation({
  mutationFn: (payload: CreateRequest) => api.create(payload),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    showSuccess(t("feature.success_create"));
    setDialogOpen(false);
  },
  onError: () => showError(t("feature.error_create")),
});
```

---

## MUI v9 パターン

### Typography スタイル（v6 breaking change 対応済み）

```tsx
// NG: v5 以前の API（MUI v6 以降は削除済み）
<ListItemText primaryTypographyProps={{ variant: 'body2' }} />

// OK: slotProps を使用
<ListItemText slotProps={{ primary: { sx: { fontSize: '0.875rem' } } }} />
```

### sx プロパティ

```tsx
// NG: 固定 pixel（テーマ非連動）
<Box sx={{ padding: '16px', fontSize: '14px' }} />

// OK: テーマスペーシングトークン
<Box sx={{ p: 2, typography: 'body2' }} />
```

### ダイアログパターン

```tsx
<Dialog
  open={dialogOpen}
  onClose={() => setDialogOpen(false)}
  maxWidth="sm"
  fullWidth
>
  <DialogTitle>
    {editTarget ? t("feature.edit") : t("feature.create")}
  </DialogTitle>
  <DialogContent>
    <TextField
      label={t("feature.field_name")}
      value={form.name}
      onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
      fullWidth
      required
      margin="dense"
    />
  </DialogContent>
  <DialogActions>
    <Button onClick={() => setDialogOpen(false)}>{t("common.cancel")}</Button>
    <Button
      variant="contained"
      onClick={handleSubmit}
      disabled={mutation.isPending}
    >
      {t("common.save")}
    </Button>
  </DialogActions>
</Dialog>
```

---

## ルーティング規約（App.tsx）

```tsx
// NG: 静的インポート（初期バンドルを肥大化させる）
import RegWatchUrlPage from "./pages/SCR023_RegWatchUrlPage";

// OK: lazy import（コード分割）
const RegWatchUrlPage = lazy(() => import("./pages/SCR023_RegWatchUrlPage"));

// ルート定義
<Route path="tasks/reg-watch-urls" element={<RegWatchUrlPage />} />;
```

---

## 定数・Enum 規約

```typescript
// NG: コンポーネント内にマジックストリング
if (status === 'active') { ... }

// OK: as const で定数化（→ constants-enums.typescript.instructions.md を参照）
const INTERVAL_OPTIONS = ['daily', 'weekly', 'monthly'] as const;
type IntervalOption = typeof INTERVAL_OPTIONS[number];
```

---

## エラー表示パターン

```tsx
// ローディング
if (isLoading) return <Skeleton variant="rectangular" height={200} />;

// エラー
if (error) return <Alert severity="error">{t("common.error_generic")}</Alert>;

// 空データ
if (!data || data.length === 0)
  return <Typography>{t("common.no_data")}</Typography>;
```

---

## 禁止事項

- `any` 型の使用（L1 相当）
- `useState` で非同期サーバー状態を管理する（TanStack Query を使うこと）
- axios 直接インポート（`import apiClient from '../api/client'` 経由で統一）
- `console.log` の本番コードへの混入
- MUI の deprecated API（`primaryTypographyProps` など MUI v5 以前の API）
- `as unknown as T` のような二重アサーション
- コンポーネントファイルに型定義・API 関数を同居させる（`types.ts` / `apis.ts` に集約）
