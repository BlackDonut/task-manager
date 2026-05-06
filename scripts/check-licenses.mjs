#!/usr/bin/env node
/**
 * check-licenses.mjs
 *
 * Python (pip-licenses) と npm (license-checker-rseidelsohn) の
 * 両依存パッケージについてコピーレフトライセンスを検出する。
 *
 * 実行: node scripts/check-licenses.mjs
 *
 * ブロック対象: GPL / LGPL / AGPL（全バージョン）
 * 終了コード: 0 = 違反なし, 1 = 違反あり（CI でブロック）
 *
 * copilot-instructions.md L1 ルール準拠:
 *   「コピーレフトライセンス（GPL / LGPL / AGPL 等）のパッケージを
 *     新規依存として提案・追加する（CI 禁止扱い → scripts/check-licenses.mjs）」
 */

import { execSync, spawnSync } from "child_process";
import { existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

// ================================================================
// ブロック対象ライセンスパターン（コピーレフト）
// ================================================================

/** @type {RegExp[]} */
const BLOCKED_PATTERNS = [
    /\bGPL[-\s]?\d/i,                        // GPL-2.0, GPL-3.0 など
    /\bGPL\b/i,                              // GPL（バージョン未記載）
    /GNU\s+General\s+Public\s+License/i,
    /\bLGPL[-\s]?\d/i,                       // LGPL-2.0, LGPL-2.1, LGPL-3.0 など
    /\bLGPL\b/i,                             // LGPL（バージョン未記載）
    /GNU\s+Lesser\s+General\s+Public\s+License/i,
    /\bAGPL[-\s]?\d/i,                       // AGPL-3.0 など
    /\bAGPL\b/i,                             // AGPL（バージョン未記載）
    /GNU\s+Affero\s+General\s+Public\s+License/i,
];

/**
 * classpath exception 付き GPL など、商用利用可能な例外を許可する。
 * @type {RegExp[]}
 */
const ALLOWED_EXCEPTIONS = [
    /GPL.*classpath.*exception/i,
    /GPL.*with.*exception/i,
];

/**
 * ライセンス文字列がブロック対象かどうかを判定する。
 * 複数ライセンスが "AND" / "OR" / ";" で連結されている場合はすべてを検査する。
 * @param {string | undefined} license
 * @returns {boolean}
 */
function isBlocked(license) {
    const normalized = (license ?? "").trim();
    if (!normalized || normalized === "UNKNOWN") return false;

    // "MIT OR GPL-2.0" のような複合表記を個々に分割して検査
    const parts = normalized.split(/\s*(?:AND|OR|;|,)\s*/i);
    return parts.some((part) => {
        if (ALLOWED_EXCEPTIONS.some((p) => p.test(part))) return false;
        return BLOCKED_PATTERNS.some((p) => p.test(part));
    });
}

let hasViolation = false;

// ================================================================
// Python: pip-licenses
// ================================================================

console.log("\n📦 Python パッケージのライセンスチェック...");

try {
    const raw = execSync(
        "pip-licenses --format=json --with-license-file --no-license-path",
        { cwd: ROOT, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] },
    );

    /** @type {Array<{ Name: string; Version: string; License: string }>} */
    const packages = JSON.parse(raw);
    const violations = packages.filter((pkg) => isBlocked(pkg.License));

    if (violations.length > 0) {
        console.error(`\n❌ Python — コピーレフトライセンスが検出されました (${violations.length} 件):`);
        for (const pkg of violations) {
            console.error(`   ${pkg.Name} @ ${pkg.Version}  [${pkg.License}]`);
        }
        hasViolation = true;
    } else {
        console.log(`   ✅ ${packages.length} パッケージ — 違反なし`);
    }
} catch (err) {
    const msg = (err.message ?? String(err)).split("\n")[0];
    if (/pip.licenses.*not found|No such file|command not found/i.test(msg)) {
        console.warn("   ⚠ pip-licenses が見つかりません。スキップ（pip install pip-licenses で導入できます）");
    } else {
        console.error("   ✗ Python ライセンスチェックに失敗しました:", msg);
        hasViolation = true;
    }
}

// ================================================================
// npm: license-checker-rseidelsohn
// ================================================================

console.log("\n📦 npm パッケージのライセンスチェック...");

const frontendDir = join(ROOT, "frontend");
const checkerScript = join(
    frontendDir,
    "node_modules",
    "license-checker-rseidelsohn",
    "bin",
    "license-checker-rseidelsohn.js",
);

if (!existsSync(frontendDir)) {
    console.warn("   ⚠ frontend/ ディレクトリが見つかりません。スキップします。");
} else if (!existsSync(checkerScript)) {
    console.warn(
        "   ⚠ license-checker-rseidelsohn が見つかりません（npm install 未実行？）。スキップします。",
    );
} else {
    try {
        // Windows の .ps1/.cmd ラッパー経由では stderr がプロセス終了コードに影響するため、
        // Node.js を直接実行してラッパーを迂回する。
        const result = spawnSync(
            process.execPath,
            [checkerScript, "--json", "--excludePrivatePackages"],
            { cwd: frontendDir, encoding: "utf8" },
        );

        if (result.status !== 0) {
            throw new Error(`exit ${result.status}: ${(result.stderr ?? "").split("\n")[0]}`);
        }

        /**
         * @type {Record<string, { licenses: string; repository?: string }>}
         */
        const packages = JSON.parse(result.stdout);
        const entries = Object.entries(packages);
        const violations = entries.filter(([, info]) => isBlocked(info.licenses));

        if (violations.length > 0) {
            console.error(`\n❌ npm — コピーレフトライセンスが検出されました (${violations.length} 件):`);
            for (const [name, info] of violations) {
                console.error(`   ${name}  [${info.licenses}]`);
            }
            hasViolation = true;
        } else {
            console.log(`   ✅ ${entries.length} パッケージ — 違反なし`);
        }
    } catch (err) {
        console.error(
            "   ✗ npm ライセンスチェックに失敗しました:",
            (err.message ?? String(err)).split("\n")[0],
        );
        hasViolation = true;
    }
}

// ================================================================
// 結果サマリー
// ================================================================

if (hasViolation) {
    console.error("\n🚫 コピーレフトライセンス違反が検出されました。");
    console.error("   GPL / LGPL / AGPL ライセンスのパッケージは本プロジェクトに追加できません。");
    console.error("   詳細は .github/copilot-instructions.md L1 ルールを参照してください。");
    process.exit(1);
} else {
    console.log("\n✅ ライセンスチェック完了 — 違反なし");
    process.exit(0);
}
