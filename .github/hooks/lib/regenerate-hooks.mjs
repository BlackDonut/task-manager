#!/usr/bin/env node
/**
 * pre-tool-safety.mjs と post-tool-safety.mjs を
 * 共有パターンライブラリ参照版に再生成する。
 *
 * 実行: node .github/hooks/lib/regenerate-hooks.mjs
 */

import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCRIPTS_DIR = join(__dirname, "..", "scripts");

// ================================================================
// pre-tool-safety.mjs
// ================================================================
const preToolContent = `#!/usr/bin/env node
/**
 * PreToolUse セーフティフック
 * 破壊的・不可逆的な操作をブロックまたは確認要求する。
 * 入力: stdin から JSON { tool_name, tool_input }
 * 出力: stdout に JSON { hookSpecificOutput: { hookEventName, permissionDecision, permissionDecisionReason } }
 *
 * 検証シナリオ（想定動作）:
 *   - alembic の upgrade コマンド → 確認要求（CONFIRM）
 *   - alembic の downgrade base コマンド → ブロック（DENY）
 *   - pnpm の publish コマンド → 確認要求（CONFIRM）
 *   - 再帰的強制削除（大文字フラグ含む）→ ブロック（DENY）
 *   - docker system prune → 確認要求（CONFIRM）
 *   - .github/hooks/ 配下のファイル内容はパターン定義のため検査対象外
 */

import { createInterface } from "readline";
import { PRE_BLOCKED, PRE_CONFIRM } from "../lib/patterns.mjs";

// hooks/ 自身のファイルはパターン定義を含むため検査対象外
const HOOKS_PATH_PATTERN = /\\.github[\\\\\\/]hooks[\\\\\\/]/;

async function main() {
  const rl = createInterface({ input: process.stdin, terminal: false });
  let raw = "";
  for await (const line of rl) {
    raw += line;
  }

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    // パース不可 — 許可
    process.exit(0);
  }

  const toolName = input?.tool_name ?? "";
  const toolInput = input?.tool_input ?? {};

  // hooks/ 配下のファイル操作はパターン定義を含むため検査スキップ
  const filePath = toolInput?.filePath ?? toolInput?.file_path ?? "";
  if (HOOKS_PATH_PATTERN.test(filePath)) {
    process.exit(0);
  }

  const serialized = JSON.stringify(toolInput);

  // ブロックパターンをチェック
  for (const rule of PRE_BLOCKED) {
    if (rule.pattern.test(serialized)) {
      const output = {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: \`ブロック: \${rule.name} — 破壊的パターンに一致しました。続行する前に明示的なユーザー確認を求めてください。\`,
        },
      };
      process.stdout.write(JSON.stringify(output));
      process.exit(0);
    }
  }

  // 確認パターンをチェック
  for (const rule of PRE_CONFIRM) {
    if (rule.pattern.test(serialized)) {
      const output = {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "ask",
          permissionDecisionReason: \`確認が必要です: \${rule.name} — 不可逆的な操作に一致しました。\`,
        },
      };
      process.stdout.write(JSON.stringify(output));
      process.exit(0);
    }
  }

  // 許可
  process.exit(0);
}

main().catch(() => process.exit(0));
`;

// ================================================================
// post-tool-safety.mjs
// ================================================================
const postToolContent = `#!/usr/bin/env node
/**
 * PostToolUse セーフティフック
 * ファイル編集ツール実行後に以下を検出・警告する:
 *   - L1 違反パターンの導入（Python / TypeScript 両対応）
 *   - L2 警告パターンの導入（Python）
 *   - TODO(security) コメントの削除
 *   - delete_flg / deleteFlg フィルタの削除（論理削除フィルタ漏れ）
 *
 * 入力: stdin から JSON { tool_name, tool_input, tool_output }
 * 出力: stdout に JSON { hookSpecificOutput: { ... } }
 *
 * 検証シナリオ（想定動作）:
 *   - newString に \`: Any\` を含む Python 編集 → L1 警告
 *   - newString に \`datetime.now()\` を含む Python 編集 → L2 警告
 *   - newString に \`: any\` を含む TS 編集 → L1 警告
 *   - newString に \`dangerouslySetInnerHTML\` を含む TS 編集 → L1 警告
 *   - oldString に \`TODO(security)\` を含み newString に含まない → 警告
 *   - oldString に \`delete_flg == 0\` を含み newString に含まない → 警告
 *   - \`create_file\` で \`Any\` 型を含むファイルを作成 → L1 警告
 */

import { createInterface } from "readline";
import {
  POST_L1_PYTHON,
  POST_L1_TS,
  POST_L2_PYTHON,
  PROTECTED_MARKERS,
  DELETE_FLG_MARKERS,
  detectLanguage,
} from "../lib/patterns.mjs";

const FILE_EDIT_TOOLS = new Set([
  "replace_string_in_file",
  "multi_replace_string_in_file",
  "edit_file",
  "create_file",
]);

/**
 * 編集対象の newString 一覧を収集する。
 * ツールごとにフィールドが異なるため分岐する。
 * @param {string} toolName
 * @param {Record<string, unknown>} toolInput
 * @returns {{ filePath: string; oldStrings: string[]; newStrings: string[] }}
 */
function collectStrings(toolName, toolInput) {
  /** @type {string[]} */
  const oldStrings = [];
  /** @type {string[]} */
  const newStrings = [];
  let filePath = "";

  if (toolName === "create_file") {
    filePath = /** @type {string} */ (toolInput?.filePath ?? "");
    const content = /** @type {string} */ (toolInput?.content ?? "");
    newStrings.push(content);
  } else if (toolName === "multi_replace_string_in_file") {
    const replacements = /** @type {Array<Record<string, string>>} */ (
      toolInput?.replacements ?? []
    );
    for (const r of replacements) {
      oldStrings.push(r?.oldString ?? "");
      newStrings.push(r?.newString ?? "");
      if (!filePath) filePath = r?.filePath ?? "";
    }
  } else {
    filePath = /** @type {string} */ (toolInput?.filePath ?? "");
    oldStrings.push(
      /** @type {string} */ (
        toolInput?.oldString ?? toolInput?.old_string ?? ""
      ),
    );
    newStrings.push(
      /** @type {string} */ (
        toolInput?.newString ?? toolInput?.new_string ?? ""
      ),
    );
  }

  return { filePath, oldStrings, newStrings };
}

async function main() {
  const rl = createInterface({ input: process.stdin, terminal: false });
  let raw = "";
  for await (const line of rl) {
    raw += line;
  }

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const toolName = input?.tool_name ?? "";

  // ファイル編集ツール以外は無視
  if (!FILE_EDIT_TOOLS.has(toolName)) {
    process.exit(0);
  }

  const toolInput = input?.tool_input ?? {};
  const { filePath, oldStrings, newStrings } = collectStrings(toolName, toolInput);

  // 言語判定: ファイル拡張子から Python / TypeScript / unknown
  const lang = detectLanguage(filePath);

  // 言語に応じた L1 パターンを選択
  const l1Patterns =
    lang === "python"
      ? POST_L1_PYTHON
      : lang === "typescript"
        ? POST_L1_TS
        : [...POST_L1_PYTHON, ...POST_L1_TS]; // 不明 → 全パターン適用

  // L2 は Python のみ
  const l2Patterns = lang === "python" || lang === "unknown" ? POST_L2_PYTHON : [];

  /** @type {string[]} */
  const notifications = [];

  // --- 保護マーカー削除検出 ---
  for (const marker of PROTECTED_MARKERS) {
    let oldHas = false;
    let newHas = false;
    for (const s of oldStrings) {
      if (marker.pattern.test(s)) oldHas = true;
    }
    for (const s of newStrings) {
      if (marker.pattern.test(s)) newHas = true;
    }
    if (oldHas && !newHas) {
      notifications.push(\`⚠️ \${marker.message}\`);
    }
  }

  // --- delete_flg フィルタ削除検出（Python snake_case + TS camelCase） ---
  for (const marker of DELETE_FLG_MARKERS) {
    let oldHas = false;
    let newHas = false;
    for (const s of oldStrings) {
      if (marker.pattern.test(s)) oldHas = true;
    }
    for (const s of newStrings) {
      if (marker.pattern.test(s)) newHas = true;
    }
    if (oldHas && !newHas) {
      notifications.push(\`⚠️ \${marker.message}\`);
    }
  }

  // --- L1 違反パターンの導入検出 ---
  for (const s of newStrings) {
    for (const rule of l1Patterns) {
      if (rule.pattern.test(s)) {
        notifications.push(
          \`⛔ L1 違反: [\${rule.name}] が検出されました。このコードはチェックインできません。編集を取り消してください。\`,
        );
      }
    }
  }

  // --- L2 警告パターンの導入検出 ---
  for (const s of newStrings) {
    for (const rule of l2Patterns) {
      if (rule.pattern.test(s)) {
        notifications.push(
          \`⚠️ L2 警告: [\${rule.name}] が検出されました。修正を検討してください。\`,
        );
      }
    }
  }

  // 全ての通知を結合して出力
  if (notifications.length > 0) {
    const output = {
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        notification: notifications.join("\\n"),
      },
    };
    process.stdout.write(JSON.stringify(output));
  }

  process.exit(0);
}

main().catch(() => process.exit(0));
`;

// --- 書き出し ---
writeFileSync(join(SCRIPTS_DIR, "pre-tool-safety.mjs"), preToolContent, "utf8");
writeFileSync(join(SCRIPTS_DIR, "post-tool-safety.mjs"), postToolContent, "utf8");

console.log("pre-tool-safety.mjs regenerated");
console.log("post-tool-safety.mjs regenerated");
