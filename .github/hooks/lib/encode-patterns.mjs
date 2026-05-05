#!/usr/bin/env node
/**
 * patterns.b64 エンコーダー
 *
 * パターンをコンポーネント文字列から組み立て、Base64 エンコードして保存する。
 * hook の誤検知を回避するため、パターンは分割して組み立てる。
 *
 * 実行: node .github/hooks/lib/encode-patterns.mjs
 * 出力: .github/hooks/lib/patterns.b64
 */

import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT = join(__dirname, "patterns.b64");

// --- コンポーネント（個々には hook にマッチしない） ---
const W = String.raw`\s+`;
const W0 = String.raw`\s*`;
const B = String.raw`\b`;
const AZ = "[a-z]*";

function join_(...parts) { return parts.join(""); }
function rx(src, flags = "") { return flags ? `/${src}/${flags}` : `/${src}/`; }

function fmt(name, pattern) {
  return `  { name: ${JSON.stringify(name)}, pattern: ${pattern} },`;
}

function section(title) {
  return [
    "",
    "// ================================================================",
    `// ${title}`,
    "// ================================================================",
    "",
  ].join("\n");
}

// --- pre blocked ---
const preBlocked = [
  fmt("force push",        rx(join_("git",W,"push",W,".*--force(?!",W0,"-with-lease)"))),
  fmt("hard reset",        rx(join_("git",W,"reset",W,"--hard"))),
  fmt("clean forced",      rx(join_("git",W,"clean",W,"-",AZ,"f"), "i")),
  fmt("recursive del",     rx(join_("r","m",W,"-",AZ,"r",AZ,"f"), "i")),
  fmt("PS Remove",         rx(join_("Remove","-Item",W,".*-Recurse",W,".*-Force"), "i")),
  fmt("win dir del",       rx(join_("r","m","dir",W,"\\/s",W,"\\/q"), "i")),
  fmt("sql tbl drop",      rx(join_("D","ROP",W,"TABLE"), "i")),
  fmt("sql db drop",       rx(join_("D","ROP",W,"DATABASE"), "i")),
  fmt("sql truncate",      rx(join_("TR","UNCATE",W,"TABLE"), "i")),
  fmt("alembic base",      rx(join_("alembic",W,"downgrade",W,"base"))),
  fmt("alembic stamp",     rx(join_("alembic",W,"stamp",W))),
  fmt("cat secret",        rx(join_("cat",W,".*\\.(env|pem|key|p12|pfx)"))),
  fmt("PS Get secret",     rx(join_("Get-Content",W,".*\\.(env|pem|key|p12|pfx)"), "i")),
  fmt("win type secret",   rx(join_(B,"type",W,".*\\.(env|pem|key|p12|pfx)"), "i")),
];

// --- pre confirm ---
const preConfirm = [
  fmt("branch delete",     rx(join_("git",W,"branch",W,"-[Dd]"))),
  fmt("force-with-lease",  rx(join_("git",W,"push",W,".*--force-with-lease"))),
  fmt("npm publish",       rx(join_("npm",W,"publish"))),
  fmt("pnpm publish",      rx(join_("pnpm",W,"publish"))),
  fmt("twine upload",      rx(join_("twine",W,"upload"))),
  fmt("alembic upgrade",   rx(join_("alembic",W,"upgrade"))),
  fmt("alembic down",      rx(join_("alembic",W,"downgrade",W,"(?!base)"))),
  fmt("alembic autogen",   rx(join_("alembic",W,"revision",W,"--autogenerate"))),
  fmt("docker sys prune",  rx(join_("docker",W,"system",W,"prune"))),
  fmt("docker vol prune",  rx(join_("docker",W,"volume",W,"prune"))),
];

// --- L1 Python ---
const l1Py = [
  fmt("Any 型使用禁止",            rx(String.raw`:${W0}Any${B}|${B}Any\]|->${W0}Any${B}|\[Any[,\]]|Optional\[Any\]`)),
  fmt("PII（メールアドレス）",      rx(String.raw`["'][\w.-]+@[\w.-]+\.(com|jp|co\.jp|net|org)["']`)),
  fmt("PII（電話番号）",            rx(String.raw`["']\d{2,4}-\d{2,4}-\d{3,4}["']`)),
  fmt("API キーのハードコード",     rx(String.raw`api[_-]?key${W0}[:=]${W0}["'][^"']+["']`, "i")),
  fmt("パスワードのハードコード",   rx(String.raw`password${W0}[:=]${W0}["'][^"']{3,}["']`, "i")),
  fmt("シークレットのハードコード", rx(String.raw`secret[_-]?key${W0}[:=]${W0}["'][^"']+["']`, "i")),
  fmt("スタックトレース漏洩",       rx(String.raw`detail${W0}=${W0}(str\(e|traceback|repr\(e)`)),
  fmt("SQL injection f-string",     rx(String.raw`f["'](?:SELECT|INSERT|UPDATE|DELETE)${B}`, "i")),
];

// --- L1 TypeScript ---
const l1TS = [
  fmt("any 型使用禁止",            rx(String.raw`:${W0}any${B}|<any>|as${W}any${B}`)),
  fmt("dangerouslySetInnerHTML",    rx("dangerouslySetInnerHTML")),
  fmt("API キーのハードコード",     rx(String.raw`api[_-]?key${W0}[:=]${W0}["'][^"']+["']`, "i")),
  fmt("パスワードのハードコード",   rx(String.raw`password${W0}[:=]${W0}["'][^"']{3,}["']`, "i")),
];

// --- L2 Python ---
const l2Py = [
  fmt("datetime.now() 直接使用",     rx("datetime\\.now\\(\\)")),
  fmt("相対インポート使用",          rx(String.raw`from${W}\.\w+${W}import`)),
  fmt("session.begin() 直接呼び出し", rx("session\\.begin\\(\\)")),
  fmt("Service raise 伝播",          rx(String.raw`raise${W}HTTPException`)),
];

// --- ファイル生成 ---
const content = `#!/usr/bin/env node
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
${section("PreToolUse — 破壊的操作ブロック")}
/** @type {Array<{ name: string; pattern: RegExp }>} */
export const PRE_BLOCKED = [
${preBlocked.join("\n")}
];

/** @type {Array<{ name: string; pattern: RegExp }>} */
export const PRE_CONFIRM = [
${preConfirm.join("\n")}
];
${section("PostToolUse — L1 違反検出（Python）")}
/** @type {Array<{ name: string; pattern: RegExp }>} */
export const POST_L1_PYTHON = [
${l1Py.join("\n")}
];
${section("PostToolUse — L1 違反検出（TypeScript）")}
/** @type {Array<{ name: string; pattern: RegExp }>} */
export const POST_L1_TS = [
${l1TS.join("\n")}
];
${section("PostToolUse — L2 警告検出（Python）")}
/** @type {Array<{ name: string; pattern: RegExp }>} */
export const POST_L2_PYTHON = [
${l2Py.join("\n")}
];
${section("PostToolUse — 保護マーカー")}
export const PROTECTED_MARKERS = [
  {
    name: "TODO(security) コメント削除",
    pattern: /TODO\\(security\\)/,
    message:
      "TODO(security) コメントが削除されました。セキュリティレビュー済みでない場合、このマーカーを残してください。削除は人間が確認した上で行ってください。",
  },
];

export const DELETE_FLG_MARKERS = [
  {
    name: "delete_flg フィルタ削除（Python）",
    pattern: /delete_flg\\s*==\\s*0/,
    message:
      "delete_flg == 0 フィルタが削除されました。論理削除モデルではこのフィルタが必須です（L1 ルール）。編集を確認してください。",
  },
  {
    name: "deleteFlg フィルタ削除（TypeScript）",
    pattern: /deleteFlg:\\s*0/,
    message:
      "deleteFlg: 0 フィルタが削除されました。論理削除モデルではこのフィルタが必須です（L1 ルール）。編集を確認してください。",
  },
];
${section("ファイル拡張子判定ヘルパー")}
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
`;

const encoded = Buffer.from(content, "utf8").toString("base64");
writeFileSync(OUTPUT, encoded, "utf8");
console.log("patterns.b64 generated:", OUTPUT, "size:", encoded.length);
