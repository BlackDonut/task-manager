#!/usr/bin/env node
/**
 * hooks テストスクリプト
 *
 * pre-tool-safety.mjs / post-tool-safety.mjs の動作を検証する。
 * 各テストケースで stdin に JSON を渡し、stdout/exit code を検査する。
 *
 * 実行: node .github/hooks/__tests__/hook-test.mjs
 */

import { execFile } from "child_process";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PRE_HOOK = join(__dirname, "..", "scripts", "pre-tool-safety.mjs");
const POST_HOOK = join(__dirname, "..", "scripts", "post-tool-safety.mjs");

let passed = 0;
let failed = 0;

/**
 * @param {string} script
 * @param {object} input
 * @returns {Promise<{ stdout: string; exitCode: number }>}
 */
function runHook(script, input) {
  return new Promise((resolve) => {
    const child = execFile("node", [script], { timeout: 10000 }, (err, stdout) => {
      resolve({ stdout: stdout ?? "", exitCode: child.exitCode ?? 0 });
    });
    child.stdin.write(JSON.stringify(input));
    child.stdin.end();
  });
}

/**
 * @param {string} name
 * @param {() => Promise<void>} fn
 */
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`  ✅ ${name}`);
  } catch (e) {
    failed++;
    console.error(`  ❌ ${name}: ${e.message}`);
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

// ================================================================
// PreToolUse テスト
// ================================================================
console.log("\n📋 PreToolUse Tests:");

await test("ブロック: force push を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "git push origin main --force" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "deny", "deny expected");
});

await test("ブロック: hard reset を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "git reset --hard HEAD~3" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "deny", "deny expected");
});

await test("ブロック: alembic downgrade base を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "alembic downgrade base" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "deny", "deny expected");
});

await test("ブロック: SQL DROP TABLE を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "sqlcmd -Q 'DROP TABLE users'" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "deny", "deny expected");
});

await test("ブロック: TRUNCATE TABLE を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "sqlcmd -Q 'TRUNCATE TABLE audit_log'" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "deny", "deny expected");
});

await test("確認: alembic upgrade を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "alembic upgrade head" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "ask", "ask expected");
});

await test("確認: docker system prune を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "docker system prune -a" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "ask", "ask expected");
});

await test("確認: twine upload を検出", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "twine upload dist/*" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "ask", "ask expected");
});

await test("許可: force-with-lease は confirm", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "git push --force-with-lease origin feature" },
  });
  const out = JSON.parse(stdout);
  assert(out.hookSpecificOutput.permissionDecision === "ask", "ask expected");
});

await test("許可: 通常コマンドはブロックしない", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "run_in_terminal",
    tool_input: { command: "python -m pytest tests/" },
  });
  assert(stdout === "", "no output expected for allowed commands");
});

await test("スキップ: hooks/ 配下はパターン検査対象外", async () => {
  const { stdout } = await runHook(PRE_HOOK, {
    tool_name: "create_file",
    tool_input: {
      filePath: ".github/hooks/lib/test.mjs",
      content: "git push --force; DROP TABLE x;",
    },
  });
  assert(stdout === "", "hooks path should be skipped");
});

// ================================================================
// PostToolUse テスト
// ================================================================
console.log("\n📋 PostToolUse Tests:");

await test("L1: Python Any 型を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/services/task_service.py",
      oldString: "data: str",
      newString: "data: Any",
    },
  });
  assert(stdout.includes("L1"), "L1 violation expected");
  assert(stdout.includes("Any"), "Any type expected");
});

await test("L1: Python PII メールアドレスを検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "create_file",
    tool_input: {
      filePath: "tests/test_users.py",
      content: 'email = "user@example.com"',
    },
  });
  assert(stdout.includes("L1"), "L1 violation expected");
  assert(stdout.includes("PII"), "PII expected");
});

await test("L1: Python SQL injection f-string を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/repositories/task_repo.py",
      oldString: "stmt = select(Task)",
      newString: 'query = f"SELECT * FROM tasks WHERE id = {user_id}"',
    },
  });
  assert(stdout.includes("L1"), "L1 violation expected");
  assert(stdout.includes("SQL"), "SQL injection expected");
});

await test("L1: Python スタックトレース漏洩を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/routers/tasks.py",
      oldString: 'detail="Internal error"',
      newString: "detail=str(e)",
    },
  });
  assert(stdout.includes("L1"), "L1 violation expected");
  assert(stdout.includes("スタックトレース"), "stacktrace expected");
});

await test("L1: TypeScript any 型を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "src/utils/helper.ts",
      oldString: "data: string",
      newString: "data: any",
    },
  });
  assert(stdout.includes("L1"), "L1 violation expected");
});

await test("L1: TypeScript dangerouslySetInnerHTML を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "src/components/Renderer.tsx",
      oldString: "{children}",
      newString: '<div dangerouslySetInnerHTML={{__html: content}} />',
    },
  });
  assert(stdout.includes("L1"), "L1 violation expected");
});

await test("L2: Python datetime.now() を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/services/task_service.py",
      oldString: "now = self.clock.now()",
      newString: "now = datetime.now()",
    },
  });
  assert(stdout.includes("L2"), "L2 warning expected");
  assert(stdout.includes("datetime"), "datetime expected");
});

await test("L2: Python 相対インポートを検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/services/task_service.py",
      oldString: "from app.repositories.task import TaskRepository",
      newString: "from .task import TaskRepository",
    },
  });
  assert(stdout.includes("L2"), "L2 warning expected");
  assert(stdout.includes("相対インポート"), "relative import expected");
});

await test("L2: Python session.begin() を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/repositories/task_repo.py",
      oldString: "async with self.tx():",
      newString: "async with session.begin():",
    },
  });
  assert(stdout.includes("L2"), "L2 warning expected");
  assert(stdout.includes("session.begin"), "session.begin expected");
});

await test("L2: Python raise HTTPException を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/services/task_service.py",
      oldString: 'return Err(error=AppError(type="NOT_FOUND"))',
      newString: "raise HTTPException(status_code=404)",
    },
  });
  assert(stdout.includes("L2"), "L2 warning expected");
});

await test("保護: TODO(security) 削除を検出", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/routers/auth.py",
      oldString: "# TODO(security): verify token",
      newString: "# Token verified",
    },
  });
  assert(stdout.includes("TODO(security)"), "TODO(security) warning expected");
});

await test("保護: delete_flg == 0 削除を検出 (Python)", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/repositories/task_repo.py",
      oldString: "Task.delete_flg == 0",
      newString: "Task.is_active == True",
    },
  });
  assert(stdout.includes("delete_flg"), "delete_flg warning expected");
});

await test("保護: deleteFlg: 0 削除を検出 (TypeScript)", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "src/services/task.service.ts",
      oldString: "deleteFlg: 0",
      newString: "isActive: true",
    },
  });
  assert(stdout.includes("deleteFlg"), "deleteFlg warning expected");
});

await test("許可: 正常な Python 編集は警告なし", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/services/task_service.py",
      oldString: "name: str",
      newString: "name: str | None",
    },
  });
  assert(stdout === "", "no warning expected for clean edits");
});

await test("言語判定: .py → Python パターンのみ適用", async () => {
  // TypeScript any は Python ファイルでは検出しない
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "replace_string_in_file",
    tool_input: {
      filePath: "app/config.py",
      oldString: "# config",
      newString: "data: any = None",
    },
  });
  // Python ファイルなので TS の "any" パターンは適用されない
  // しかし "any" は Python では型ヒントとして使わないのでクリーンなはず
  assert(!stdout.includes("any 型"), "TS any rule should not apply to .py");
});

await test("スキップ: 非編集ツールは無視", async () => {
  const { stdout } = await runHook(POST_HOOK, {
    tool_name: "grep_search",
    tool_input: { query: "data: Any" },
  });
  assert(stdout === "", "non-edit tools should be ignored");
});

// ================================================================
// Summary
// ================================================================
console.log(`\n📊 Results: ${passed} passed, ${failed} failed, ${passed + failed} total\n`);
process.exit(failed > 0 ? 1 : 0);
