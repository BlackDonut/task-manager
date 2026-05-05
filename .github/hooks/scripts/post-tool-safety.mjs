#!/usr/bin/env node
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
 *   - newString に `: Any` を含む Python 編集 → L1 警告
 *   - newString に `datetime.now()` を含む Python 編集 → L2 警告
 *   - newString に `: any` を含む TS 編集 → L1 警告
 *   - newString に `dangerouslySetInnerHTML` を含む TS 編集 → L1 警告
 *   - oldString に `TODO(security)` を含み newString に含まない → 警告
 *   - oldString に `delete_flg == 0` を含み newString に含まない → 警告
 *   - `create_file` で `Any` 型を含むファイルを作成 → L1 警告
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
  "apply_patch",
  "replace_string_in_file",
  "multi_replace_string_in_file",
  "edit_file",
  "create_file",
]);

/**
 * apply_patch の入力を簡易解析し、ファイルごとの追加・削除文字列を抽出する。
 * @param {string} patchText
 * @returns {Array<{ filePath: string; oldStrings: string[]; newStrings: string[] }>}
 */
function parseApplyPatchInput(patchText) {
  const lines = patchText.split(/\r?\n/);
  /** @type {string[]} */
  let oldStrings = [];
  /** @type {string[]} */
  let newStrings = [];
  /** @type {Array<{ filePath: string; oldStrings: string[]; newStrings: string[] }> } */
  const edits = [];
  let filePath = "";

  const pushCurrent = () => {
    if (!filePath) {
      return;
    }
    edits.push({ filePath, oldStrings, newStrings });
    filePath = "";
    oldStrings = [];
    newStrings = [];
  };

  for (const line of lines) {
    const fileMatch = line.match(/^\*\*\* (?:Update|Add|Delete) File:\s+(.+)$/);
    if (fileMatch) {
      pushCurrent();
      filePath = fileMatch[1].trim();
      continue;
    }

    if (!filePath) {
      continue;
    }

    if (line.startsWith("-") && !line.startsWith("---")) {
      oldStrings.push(line.slice(1));
      continue;
    }

    if (line.startsWith("+") && !line.startsWith("+++")) {
      newStrings.push(line.slice(1));
    }
  }

  pushCurrent();
  return edits;
}

/**
 * 編集対象の文字列一覧を収集する。
 * ツールごとにフィールドが異なるため分岐する。
 * @param {string} toolName
 * @param {Record<string, unknown>} toolInput
 * @returns {Array<{ filePath: string; oldStrings: string[]; newStrings: string[] }>}
 */
function collectEdits(toolName, toolInput) {
  /** @type {string[]} */
  const oldStrings = [];
  /** @type {string[]} */
  const newStrings = [];
  let filePath = "";

  if (toolName === "apply_patch") {
    return parseApplyPatchInput(/** @type {string} */ (toolInput?.input ?? ""));
  }

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

  return [{ filePath, oldStrings, newStrings }];
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
  const edits = collectEdits(toolName, toolInput);

  /** @type {string[]} */
  const notifications = [];

  for (const edit of edits) {
    const lang = detectLanguage(edit.filePath);
    const l1Patterns =
      lang === "python"
        ? POST_L1_PYTHON
        : lang === "typescript"
          ? POST_L1_TS
          : [...POST_L1_PYTHON, ...POST_L1_TS];
    const l2Patterns = lang === "python" || lang === "unknown" ? POST_L2_PYTHON : [];

    for (const marker of PROTECTED_MARKERS) {
      let oldHas = false;
      let newHas = false;
      for (const s of edit.oldStrings) {
        if (marker.pattern.test(s)) oldHas = true;
      }
      for (const s of edit.newStrings) {
        if (marker.pattern.test(s)) newHas = true;
      }
      if (oldHas && !newHas) {
        notifications.push(`⚠️ ${marker.message}`);
      }
    }

    for (const marker of DELETE_FLG_MARKERS) {
      let oldHas = false;
      let newHas = false;
      for (const s of edit.oldStrings) {
        if (marker.pattern.test(s)) oldHas = true;
      }
      for (const s of edit.newStrings) {
        if (marker.pattern.test(s)) newHas = true;
      }
      if (oldHas && !newHas) {
        notifications.push(`⚠️ ${marker.message}`);
      }
    }

    for (const s of edit.newStrings) {
      for (const rule of l1Patterns) {
        if (rule.pattern.test(s)) {
          notifications.push(
            `⛔ L1 違反: [${rule.name}] が検出されました。このコードはチェックインできません。編集を取り消してください。`,
          );
        }
      }
    }

    for (const s of edit.newStrings) {
      for (const rule of l2Patterns) {
        if (rule.pattern.test(s)) {
          notifications.push(
            `⚠️ L2 警告: [${rule.name}] が検出されました。修正を検討してください。`,
          );
        }
      }
    }
  }

  // 全ての通知を結合して出力
  if (notifications.length > 0) {
    const output = {
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        notification: notifications.join("\n"),
      },
    };
    process.stdout.write(JSON.stringify(output));
  }

  process.exit(0);
}

main().catch(() => process.exit(0));
