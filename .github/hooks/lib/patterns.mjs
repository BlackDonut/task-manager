#!/usr/bin/env node
/**
 * 共有パターン定義
 *
 * hooks/ と scripts/ の両方から参照される L1/L2 パターンの SSOT。
 * パターン追加・修正は必ずこのファイルで行い、各 hook/script は import して使う。
 *
 * 分類:
 *   - PRE_BLOCKED / PRE_CONFIRM: PreToolUse で使用（破壊的操作の検出）
 *   - POST_L1_PYTHON / POST_L1_TS: PostToolUse で使用（L1 違反の検出）
 *   - POST_L2_PYTHON: PostToolUse で使用（L2 警告の検出）
 *   - PROTECTED_MARKERS / DELETE_FLG_MARKERS: PostToolUse で使用（保護マーカー削除の検出）
 *
 * ⚠️ このファイルは generate-patterns.mjs で自動生成される。直接編集しない。
 * ⚠️ パターンの追加・修正は encode-patterns.mjs を編集し再生成する。
 */

// ================================================================
// PreToolUse — 破壊的操作ブロック
// ================================================================

/** @type {Array<{ name: string; pattern: RegExp }>} */
export const PRE_BLOCKED = [
  { name: "force push", pattern: /git\s+push\s+.*--force(?!\s*-with-lease)/ },
  { name: "hard reset", pattern: /git\s+reset\s+--hard/ },
  { name: "clean forced", pattern: /git\s+clean\s+-[a-z]*f/i },
  { name: "recursive del", pattern: /rm\s+-[a-z]*r[a-z]*f/i },
  { name: "PS Remove", pattern: /Remove-Item\s+.*-Recurse\s+.*-Force/i },
  { name: "win dir del", pattern: /rmdir\s+\/s\s+\/q/i },
  { name: "sql tbl drop", pattern: /DROP\s+TABLE/i },
  { name: "sql db drop", pattern: /DROP\s+DATABASE/i },
  { name: "sql truncate", pattern: /TRUNCATE\s+TABLE/i },
  { name: "alembic base", pattern: /alembic\s+downgrade\s+base/ },
  { name: "alembic stamp", pattern: /alembic\s+stamp\s+/ },
  { name: "cat secret", pattern: /cat\s+.*\.(env|pem|key|p12|pfx)/ },
  { name: "PS Get secret", pattern: /Get-Content\s+.*\.(env|pem|key|p12|pfx)/i },
  { name: "win type secret", pattern: /\btype\s+.*\.(env|pem|key|p12|pfx)/i },
];

/** @type {Array<{ name: string; pattern: RegExp }>} */
export const PRE_CONFIRM = [
  { name: "governance file edit", pattern: /\.github[\\/](copilot-instructions\.md|GUIDE\.md|(instructions|agents|prompts)[\\/])/ },
  { name: "branch delete", pattern: /git\s+branch\s+-[Dd]/ },
  { name: "force-with-lease", pattern: /git\s+push\s+.*--force-with-lease/ },
  { name: "npm publish", pattern: /npm\s+publish/ },
  { name: "pnpm publish", pattern: /pnpm\s+publish/ },
  { name: "eslint autofix", pattern: /eslint\s+.*--fix\b/ },
  { name: "ruff format write", pattern: /ruff\s+format(?!\s+--check)\b/ },
  { name: "ruff check fix", pattern: /ruff\s+check\s+.*--fix\b/ },
  { name: "twine upload", pattern: /twine\s+upload/ },
  { name: "alembic upgrade", pattern: /alembic\s+upgrade/ },
  { name: "alembic down", pattern: /alembic\s+downgrade\s+(?!base)/ },
  { name: "alembic autogen", pattern: /alembic\s+revision\s+--autogenerate/ },
  { name: "docker sys prune", pattern: /docker\s+system\s+prune/ },
  { name: "docker vol prune", pattern: /docker\s+volume\s+prune/ },
  { name: "file delete", pattern: /(^|\s)(rm|del)\s+(?!-)/i },
  { name: "PS remove item", pattern: /Remove-Item\b/i },
  { name: "win rmdir", pattern: /\brmdir\b/i },
];

// ================================================================
// PostToolUse — L1 違反検出（Python）
// ================================================================

/** @type {Array<{ name: string; pattern: RegExp }>} */
export const POST_L1_PYTHON = [
  { name: "Any 型使用禁止", pattern: /:\s*Any\b|\bAny\]|->\s*Any\b|\[Any[,\]]|Optional\[Any\]/ },
  { name: "PII（メールアドレス）", pattern: /["'][\w.-]+@[\w.-]+\.(com|jp|co\.jp|net|org)["']/ },
  { name: "PII（電話番号）", pattern: /["']\d{2,4}-\d{2,4}-\d{3,4}["']/ },
  { name: "API キーのハードコード", pattern: /api[_-]?key\s*[:=]\s*["'][^"']+["']/i },
  { name: "パスワードのハードコード", pattern: /password\s*[:=]\s*["'][^"']{3,}["']/i },
  { name: "シークレットのハードコード", pattern: /secret[_-]?key\s*[:=]\s*["'][^"']+["']/i },
  { name: "スタックトレース漏洩", pattern: /detail\s*=\s*(str\(e|traceback|repr\(e)/ },
  { name: "SQL injection f-string", pattern: /f["'](?:SELECT|INSERT|UPDATE|DELETE)\b/i },
];

// ================================================================
// PostToolUse — L1 違反検出（TypeScript）
// ================================================================

/** @type {Array<{ name: string; pattern: RegExp }>} */
export const POST_L1_TS = [
  { name: "any 型使用禁止", pattern: /:\s*any\b|<any>|as\s+any\b/ },
  { name: "dangerouslySetInnerHTML", pattern: /dangerouslySetInnerHTML/ },
  { name: "API キーのハードコード", pattern: /api[_-]?key\s*[:=]\s*["'][^"']+["']/i },
  { name: "パスワードのハードコード", pattern: /password\s*[:=]\s*["'][^"']{3,}["']/i },
];

// ================================================================
// PostToolUse — L2 警告検出（Python）
// ================================================================

/** @type {Array<{ name: string; pattern: RegExp }>} */
export const POST_L2_PYTHON = [
  { name: "datetime.now() 直接使用", pattern: /datetime\.now\(\)/ },
  { name: "相対インポート使用", pattern: /from\s+\.\w+\s+import/ },
  { name: "session.begin() 直接呼び出し", pattern: /session\.begin\(\)/ },
  { name: "Service raise 伝播", pattern: /raise\s+HTTPException/ },
];

// ================================================================
// PostToolUse — 保護マーカー
// ================================================================

export const PROTECTED_MARKERS = [
  {
    name: "TODO(security) コメント削除",
    pattern: /TODO\(security\)/,
    message:
      "TODO(security) コメントが削除されました。セキュリティレビュー済みでない場合、このマーカーを残してください。削除は人間が確認した上で行ってください。",
  },
];

export const DELETE_FLG_MARKERS = [
  {
    name: "delete_flg フィルタ削除（Python）",
    pattern: /delete_flg\s*==\s*0/,
    message:
      "delete_flg == 0 フィルタが削除されました。論理削除モデルではこのフィルタが必須です（L1 ルール）。編集を確認してください。",
  },
  {
    name: "deleteFlg フィルタ削除（TypeScript）",
    pattern: /deleteFlg:\s*0/,
    message:
      "deleteFlg: 0 フィルタが削除されました。論理削除モデルではこのフィルタが必須です（L1 ルール）。編集を確認してください。",
  },
];

// ================================================================
// ファイル拡張子判定ヘルパー
// ================================================================

/**
 * ファイルパスから Python / TypeScript を判定する。
 * @param {string} filePath
 * @returns {"python" | "typescript" | "unknown"}
 */
export function detectLanguage(filePath) {
  if (!filePath) return "unknown";
  if (filePath.endsWith(".py")) return "python";
  if (
    filePath.endsWith(".ts") ||
    filePath.endsWith(".tsx") ||
    filePath.endsWith(".js") ||
    filePath.endsWith(".jsx") ||
    filePath.endsWith(".mjs")
  ) {
    return "typescript";
  }
  return "unknown";
}
