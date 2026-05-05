#!/usr/bin/env node
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
const HOOKS_PATH_PATTERN = /\.github[\\\/]hooks[\\\/]/;

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
          permissionDecisionReason: `ブロック: ${rule.name} — 破壊的パターンに一致しました。続行する前に明示的なユーザー確認を求めてください。`,
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
          permissionDecisionReason: `確認が必要です: ${rule.name} — 不可逆的な操作に一致しました。`,
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
